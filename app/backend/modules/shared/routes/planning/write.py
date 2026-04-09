import logging
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs, UserRole
from models.plannings import Plannings, PlanningType
from models.planning_machines import Planning_machines
from models.planning_utilisateurs import Planning_utilisateurs
from services.plannings import PlanningsService
from services.planning_utilisateurs import Planning_utilisateursService
from tasks.planning_emails import send_planning_assignment_emails
from .schemas import PlanningResponse, PlanningCreateData
from .helpers import verify_admin, send_planning_notifications, _serialize_planning_for_email

router = APIRouter(prefix="/api/v1/plannings", tags=["plannings"])
logger = logging.getLogger(__name__)


@router.post("", response_model=PlanningResponse, status_code=status.HTTP_201_CREATED)
async def create_planning(
    data: PlanningCreateData,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new planning (admin only)"""
    await verify_admin(current_user)
    
    try:
        # Create planning directly without service to avoid greenlet_spawn
        planning_data = {
            "identifiant_planning": data.identifiant_planning,
            "date_debut": data.date_debut,
            "date_fin": data.date_fin,
            "type": data.type,
            "shift_type": data.shift_type,
            "chef_operation_id": data.chef_operation_id,
            "chef_technique_id": data.chef_technique_id,
            "zone_travail": data.zone_travail,
            "created_at": datetime.now()
        }
        
        planning = Plannings(**planning_data)
        db.add(planning)
        await db.commit()
        await db.refresh(planning)
        
        if not planning:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create planning"
            )
        
        # Capture only the ID immediately to avoid greenlet_spawn issues
        planning_id = planning.id
        
        # Create response data without accessing planning object attributes
        planning_response_data = {
            "id": planning_id,
            "identifiant_planning": data.identifiant_planning,
            "date_debut": data.date_debut,
            "date_fin": data.date_fin,
            "type": data.type,
            "shift_type": data.shift_type,
            "chef_operation_id": data.chef_operation_id,
            "chef_technique_id": data.chef_technique_id,
            "zone_travail": data.zone_travail,
            "created_at": datetime.now(),
            "assigned_users": [],
            "machine_ids": [],
        }

        if data.machine_ids:
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
        
        # Assign users (dedupe + single commit)
        user_ids_set = set()
        if data.chef_operation_id:
            user_ids_set.add(data.chef_operation_id)
        if data.chef_technique_id:
            user_ids_set.add(data.chef_technique_id)
        if data.technicien_ids:
            user_ids_set.update(data.technicien_ids)

        all_assigned_users = list(user_ids_set)

        # Enforce user shift availability for SHIFT plannings
        if data.type == PlanningType.SHIFT.value and data.shift_type and all_assigned_users:
            mismatched_result = await db.execute(
                select(Utilisateurs.id)
                .where(Utilisateurs.id.in_(all_assigned_users))
                .where(Utilisateurs.shift_type != data.shift_type)
            )
            mismatched_ids = [row[0] for row in mismatched_result.fetchall()]
            if mismatched_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Users {mismatched_ids} do not match planning shift_type {data.shift_type}",
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
            await send_planning_notifications(db, planning_id, data.identifiant_planning, all_assigned_users)

            users_result = await db.execute(select(Utilisateurs).where(Utilisateurs.id.in_(all_assigned_users)))
            users = users_result.scalars().all()
            recipients = [{"id": u.id, "nom": u.nom, "email": u.email} for u in users if getattr(u, "email", None)]
            if recipients:
                send_planning_assignment_emails.delay(recipients, _serialize_planning_for_email(planning_response_data))
        
        # Return simple dict to avoid greenlet_spawn issues
        return planning_response_data
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating planning: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create planning: {str(e)}"
        )


@router.post("/{planning_id}/resend-emails")
async def resend_planning_emails(
    planning_id: int,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually re-send planning assignment emails to currently assigned users (admin only)."""
    await verify_admin(current_user)

    service = PlanningsService(db)
    planning = await service.get_by_id(planning_id)
    if not planning:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planning not found")

    assigned_ids_result = await db.execute(
        select(Planning_utilisateurs.utilisateur_id).where(Planning_utilisateurs.planning_id == planning_id)
    )
    user_ids = [row[0] for row in assigned_ids_result.fetchall()]

    if not user_ids:
        return {"queued": 0}

    users_result = await db.execute(select(Utilisateurs).where(Utilisateurs.id.in_(user_ids)))
    users = users_result.scalars().all()
    recipients = [{"id": u.id, "nom": u.nom, "email": u.email} for u in users if getattr(u, "email", None)]
    if not recipients:
        return {"queued": 0}

    planning_payload = _serialize_planning_for_email(
        {
            "id": planning.id,
            "identifiant_planning": planning.identifiant_planning,
            "date_debut": planning.date_debut,
            "date_fin": planning.date_fin,
            "type": planning.type.value if getattr(planning, "type", None) else "",
            "shift_type": planning.shift_type.value if getattr(planning, "shift_type", None) else None,
            "zone_travail": getattr(planning, "zone_travail", None),
        }
    )

    send_planning_assignment_emails.delay(recipients, planning_payload)
    return {"queued": len(recipients)}


@router.delete("/{planning_id}")
async def delete_planning(
    planning_id: int,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a planning (admin only)"""
    await verify_admin(current_user)
    
    try:
        # Delete associated planning_utilisateurs records first
        pu_service = Planning_utilisateursService(db)
        result = await db.execute(
            select(Planning_utilisateurs)
            .where(Planning_utilisateurs.planning_id == planning_id)
        )
        assignments = result.scalars().all()
        
        for assignment in assignments:
            await pu_service.delete(assignment.id)
        
        # Delete planning
        service = PlanningsService(db)
        success = await service.delete(planning_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Planning not found"
            )
        
        return {"message": "Planning deleted successfully", "id": planning_id}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting planning {planning_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete planning: {str(e)}"
        )
