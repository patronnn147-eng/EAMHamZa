import logging
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs, UserRole
from models.planning_machines import Planning_machines
from models.planning_utilisateurs import Planning_utilisateurs
from services.audit import AuditService, AuditEntityType
from services.plannings import PlanningsService
from tasks.planning_emails import send_planning_assignment_emails
from .schemas import PlanningResponse, PlanningUpdateData, UserOption
from .helpers import (
    verify_admin,
    send_planning_notifications,
    _serialize_planning_for_email,
    get_planning_with_users,
)

router = APIRouter(prefix="/api/v1/plannings", tags=["plannings"])
logger = logging.getLogger(__name__)


@router.get("/users/by-role/{role}", response_model=List[UserOption])
async def get_users_by_role(
    role: UserRole,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get users by role for dropdown selection"""
    await verify_admin(current_user)

    try:
        result = await db.execute(select(Utilisateurs).where(Utilisateurs.role == role))
        users = result.scalars().all()

        return [
            UserOption(
                id=user.id,
                nom=user.nom,
                email=user.email,
                role=user.role.value,
                shift_type=user.shift_type.value
                if hasattr(user.shift_type, "value")
                else (
                    str(user.shift_type) if getattr(user, "shift_type", None) else None
                ),
            )
            for user in users
        ]
    except Exception as e:
        logger.exception(f"Error fetching users by role {role}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch users: {str(e)}",
        )


@router.put("/{planning_id}", response_model=PlanningResponse)
async def update_planning(
    planning_id: int,
    data: PlanningUpdateData,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a planning (admin only)"""
    await verify_admin(current_user)
    safe_technicien_ids = repr(data.technicien_ids)
    logger.info(
        f"UPDATE planning {planning_id} — technicien_ids received: {safe_technicien_ids}"
    )

    try:
        service = PlanningsService(db)
        planning = await service.get_by_id(planning_id)

        if not planning:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Planning not found"
            )

        original_identifiant_planning = planning.identifiant_planning
        original_date_debut = planning.date_debut
        original_date_fin = planning.date_fin
        original_type = planning.type.value if planning.type else None
        original_shift_type = planning.shift_type.value if planning.shift_type else None
        original_chef_operation_id = planning.chef_operation_id
        original_chef_technique_id = planning.chef_technique_id
        original_zone_travail = getattr(planning, "zone_travail", None)
        original_created_at = planning.created_at

        # Build update dict
        update_dict = {}
        if data.identifiant_planning is not None:
            update_dict["identifiant_planning"] = data.identifiant_planning
        if data.date_debut is not None:
            update_dict["date_debut"] = data.date_debut
        if data.date_fin is not None:
            update_dict["date_fin"] = data.date_fin
        if data.type is not None:
            update_dict["type"] = data.type
        if data.shift_type is not None:
            update_dict["shift_type"] = data.shift_type
        if data.chef_operation_id is not None:
            update_dict["chef_operation_id"] = data.chef_operation_id
        if data.chef_technique_id is not None:
            update_dict["chef_technique_id"] = data.chef_technique_id
        if data.zone_travail is not None:
            update_dict["zone_travail"] = data.zone_travail

        # Update planning
        await service.update(planning_id, update_dict)

        identifiant_planning = update_dict.get(
            "identifiant_planning", original_identifiant_planning
        )

        planning_response_data = {
            "id": planning_id,
            "identifiant_planning": identifiant_planning,
            "date_debut": update_dict.get("date_debut", original_date_debut),
            "date_fin": update_dict.get("date_fin", original_date_fin),
            "type": update_dict.get("type", original_type),
            "shift_type": update_dict.get("shift_type", original_shift_type),
            "chef_operation_id": update_dict.get(
                "chef_operation_id", original_chef_operation_id
            ),
            "chef_technique_id": update_dict.get(
                "chef_technique_id", original_chef_technique_id
            ),
            "zone_travail": update_dict.get("zone_travail", original_zone_travail),
            "created_at": original_created_at,
            "assigned_users": [],
            "machine_ids": [],
        }

        # Fetch existing machine assignments before any modification
        existing_machines_result = await db.execute(
            select(Planning_machines.machine_id).where(
                Planning_machines.planning_id == planning_id
            )
        )
        existing_machine_ids = [row[0] for row in existing_machines_result.fetchall()]

        if data.machine_ids is not None and len(data.machine_ids) > 0:
            # Explicit non-empty list — replace with new set
            await db.execute(
                delete(Planning_machines).where(
                    Planning_machines.planning_id == planning_id
                )
            )
            now = datetime.now()
            for machine_id in sorted(set(data.machine_ids)):
                db.add(
                    Planning_machines(
                        planning_id=planning_id,
                        machine_id=machine_id,
                        created_at=now,
                    )
                )
            await db.commit()
            planning_response_data["machine_ids"] = sorted(set(data.machine_ids))
        else:
            # Empty or None — preserve existing machines
            planning_response_data["machine_ids"] = existing_machine_ids

        all_assigned_users: List[int] = []

        if True:  # always rebuild planning_utilisateurs to repair any missing rows
            # Fetch existing assignments so we can preserve technicians when not explicitly changed
            existing_result = await db.execute(
                select(Planning_utilisateurs.utilisateur_id).where(
                    Planning_utilisateurs.planning_id == planning_id
                )
            )
            existing_assigned_ids = {row[0] for row in existing_result.fetchall()}
            old_chef_ids = set(
                filter(None, [original_chef_operation_id, original_chef_technique_id])
            )
            existing_tech_ids = existing_assigned_ids - old_chef_ids

            user_ids_set = set()

            # Use new chef IDs if provided, otherwise keep originals
            effective_chef_op = (
                data.chef_operation_id
                if data.chef_operation_id is not None
                else original_chef_operation_id
            )
            effective_chef_tech = (
                data.chef_technique_id
                if data.chef_technique_id is not None
                else original_chef_technique_id
            )
            if effective_chef_op:
                user_ids_set.add(effective_chef_op)
            if effective_chef_tech:
                user_ids_set.add(effective_chef_tech)

            # Use new technician list if non-empty, otherwise preserve existing technicians
            if data.technicien_ids:
                user_ids_set.update(data.technicien_ids)
            else:
                user_ids_set.update(existing_tech_ids)

            all_assigned_users = list(user_ids_set)

            await db.execute(
                delete(Planning_utilisateurs).where(
                    Planning_utilisateurs.planning_id == planning_id
                )
            )

            now = datetime.now()
            for user_id in all_assigned_users:
                db.add(
                    Planning_utilisateurs(
                        planning_id=planning_id,
                        utilisateur_id=user_id,
                        created_at=now,
                    )
                )

            await db.commit()

        if all_assigned_users:
            await send_planning_notifications(
                db, planning_id, identifiant_planning, all_assigned_users
            )

            users_result = await db.execute(
                select(Utilisateurs).where(Utilisateurs.id.in_(all_assigned_users))
            )
            users = users_result.scalars().all()
            recipients = [
                {"id": u.id, "nom": u.nom, "email": u.email}
                for u in users
                if getattr(u, "email", None)
            ]
            if recipients:
                send_planning_assignment_emails.delay(
                    recipients, _serialize_planning_for_email(planning_response_data)
                )

        # Fetch updated planning with assigned users and machines using helper function
        fresh_planning = await PlanningsService(db).get_by_id(planning_id)
        updated_planning_data = await get_planning_with_users(db, fresh_planning)

        try:
            await AuditService(db).log_update(
                entity_type=AuditEntityType.PLANNING,
                entity_id=planning_id,
                old_values={
                    "identifiant_planning": original_identifiant_planning,
                    "date_debut": str(original_date_debut),
                    "date_fin": str(original_date_fin),
                    "type": original_type,
                    "shift_type": original_shift_type,
                },
                new_values={
                    k: str(v) if hasattr(v, "isoformat") else v
                    for k, v in update_dict.items()
                },
                user_id=current_user.id,
                user_name=current_user.nom,
                entity_name=identifiant_planning,
            )
        except Exception:
            logger.warning("Audit log failed for update planning %s", planning_id)

        return PlanningResponse(**updated_planning_data)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(
            f"Error updating planning {planning_id}: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update planning: {str(e)}",
        )
