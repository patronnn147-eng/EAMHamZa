import logging
from datetime import datetime
from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs, UserRole
from models.planning_machines import PlanningMachines
from models.planning_utilisateurs import PlanningUtilisateurs
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
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get users by role for dropdown selection"""
    verify_admin(current_user)

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


def _build_update_dict(data: PlanningUpdateData) -> dict:
    """Map non-None request fields to their DB column values."""
    d: dict = {}
    if data.identifiant_planning is not None:
        d["identifiant_planning"] = data.identifiant_planning
    if data.date_debut is not None:
        d["date_debut"] = data.date_debut
    if data.date_fin is not None:
        d["date_fin"] = data.date_fin
    if data.type is not None:
        d["type"] = data.type
    if data.shift_type is not None:
        d["shift_type"] = data.shift_type
    if data.chef_operation_id is not None:
        d["chef_operation_id"] = data.chef_operation_id
    if data.chef_technique_id is not None:
        d["chef_technique_id"] = data.chef_technique_id
    if data.zone_travail is not None:
        d["zone_travail"] = data.zone_travail
    return d


def _compute_user_id_set(data, original_chef_op, original_chef_tech, existing_tech_ids: set) -> set:
    """Return full set of user IDs that should be assigned after the update."""
    effective_chef_op = (
        data.chef_operation_id if data.chef_operation_id is not None else original_chef_op
    )
    effective_chef_tech = (
        data.chef_technique_id if data.chef_technique_id is not None else original_chef_tech
    )
    user_ids: set = set()
    if effective_chef_op:
        user_ids.add(effective_chef_op)
    if effective_chef_tech:
        user_ids.add(effective_chef_tech)
    if data.technicien_ids:
        user_ids.update(data.technicien_ids)
    else:
        user_ids.update(existing_tech_ids)
    return user_ids


async def _rebuild_user_assignments(
    db: AsyncSession,
    planning_id: int,
    data: PlanningUpdateData,
    original_chef_op,
    original_chef_tech,
) -> List[int]:
    """Delete and re-insert PlanningUtilisateurs, preserving existing techs when not overridden."""
    existing_result = await db.execute(
        select(PlanningUtilisateurs.utilisateur_id).where(
            PlanningUtilisateurs.planning_id == planning_id
        )
    )
    existing_assigned_ids = {row[0] for row in existing_result.fetchall()}
    old_chef_ids = set(filter(None, [original_chef_op, original_chef_tech]))
    existing_tech_ids = existing_assigned_ids - old_chef_ids

    user_ids = _compute_user_id_set(data, original_chef_op, original_chef_tech, existing_tech_ids)

    await db.execute(
        delete(PlanningUtilisateurs).where(PlanningUtilisateurs.planning_id == planning_id)
    )
    now = datetime.now()
    for user_id in user_ids:
        db.add(
            PlanningUtilisateurs(planning_id=planning_id, utilisateur_id=user_id, created_at=now)
        )
    await db.commit()
    return list(user_ids)


async def _update_machine_assignments(
    db: AsyncSession,
    planning_id: int,
    data: PlanningUpdateData,
    existing_machine_ids: List[int],
) -> List[int]:
    """Replace machine assignments if data.machine_ids is non-empty; otherwise keep existing."""
    if data.machine_ids is not None and len(data.machine_ids) > 0:
        await db.execute(
            delete(PlanningMachines).where(PlanningMachines.planning_id == planning_id)
        )
        now = datetime.now()
        for machine_id in sorted(set(data.machine_ids)):
            db.add(
                PlanningMachines(planning_id=planning_id, machine_id=machine_id, created_at=now)
            )
        await db.commit()
        return sorted(set(data.machine_ids))
    return existing_machine_ids


async def _send_planning_update_notifications(
    db: AsyncSession,
    planning_id: int,
    identifiant_planning,
    all_assigned_users: List[int],
    planning_response_data: dict,
) -> None:
    """Send planning assignment notifications and emails to all assigned users."""
    if not all_assigned_users:
        return
    await send_planning_notifications(db, planning_id, identifiant_planning, all_assigned_users)
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


async def _try_audit_update_planning(
    db: AsyncSession,
    planning_id: int,
    original_identifiant,
    original_date_debut,
    original_date_fin,
    original_type,
    original_shift_type,
    update_dict: dict,
    user_id: int,
    user_name,
    identifiant_planning,
) -> None:
    """Fire-and-forget audit log for planning update."""
    try:
        await AuditService(db).log_update(
            entity_type=AuditEntityType.PLANNING,
            entity_id=planning_id,
            old_values={
                "identifiant_planning": original_identifiant,
                "date_debut": str(original_date_debut),
                "date_fin": str(original_date_fin),
                "type": original_type,
                "shift_type": original_shift_type,
            },
            new_values={
                k: str(v) if hasattr(v, "isoformat") else v
                for k, v in update_dict.items()
            },
            user_id=user_id,
            user_name=user_name,
            entity_name=identifiant_planning,
        )
    except Exception:
        logger.warning("Audit log failed for update planning %s", planning_id)


@router.put("/{planning_id}", response_model=PlanningResponse)
async def update_planning(
    planning_id: int,
    data: PlanningUpdateData,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update a planning (admin only)"""
    verify_admin(current_user)
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

        update_dict = _build_update_dict(data)
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

        existing_machines_result = await db.execute(
            select(PlanningMachines.machine_id).where(
                PlanningMachines.planning_id == planning_id
            )
        )
        existing_machine_ids = [row[0] for row in existing_machines_result.fetchall()]
        planning_response_data["machine_ids"] = await _update_machine_assignments(
            db, planning_id, data, existing_machine_ids
        )

        all_assigned_users = await _rebuild_user_assignments(
            db, planning_id, data, original_chef_operation_id, original_chef_technique_id
        )

        await _send_planning_update_notifications(
            db, planning_id, identifiant_planning, all_assigned_users, planning_response_data
        )

        fresh_planning = await PlanningsService(db).get_by_id(planning_id)
        updated_planning_data = await get_planning_with_users(db, fresh_planning)

        await _try_audit_update_planning(
            db, planning_id,
            original_identifiant_planning, original_date_debut, original_date_fin,
            original_type, original_shift_type,
            update_dict, current_user.id, current_user.nom, identifiant_planning,
        )

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

