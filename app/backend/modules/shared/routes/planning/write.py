import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs
from models.plannings import Plannings, PlanningType, PlanningStatut
from models.planning_machines import PlanningMachines
from models.planning_utilisateurs import PlanningUtilisateurs
from services.audit import AuditService, AuditEntityType
from services.plannings import PlanningsService
from services.PlanningUtilisateurs import PlanningUtilisateursService
from tasks.planning_emails import send_planning_assignment_emails
from .schemas import PlanningResponse, PlanningCreateData
from .helpers import (
    verify_admin,
    verify_cheftech,
    send_planning_notifications,
    _serialize_planning_for_email,
    get_planning_with_users,
)
from typing import Annotated

router = APIRouter(prefix="/api/v1/plannings", tags=["plannings"])
logger = logging.getLogger(__name__)

_PLANNING_NOT_FOUND_MSG = "Planning not found"


def _resolve_planning_statut(value: str | None) -> PlanningStatut:
    """Return PlanningStatut from raw string; fall back to DRAFT on bad value."""
    if value is None:
        return PlanningStatut.DRAFT
    try:
        return PlanningStatut(value)
    except ValueError:
        return PlanningStatut.DRAFT


def _collect_user_ids(data: "PlanningCreateData") -> list:
    """Aggregate chef/tech user IDs from planning request into a deduplicated list."""
    user_ids: set = set()
    if data.chef_operation_id:
        user_ids.add(data.chef_operation_id)
    if data.chef_technique_id:
        user_ids.add(data.chef_technique_id)
    if data.technicien_ids:
        user_ids.update(data.technicien_ids)
    return list(user_ids)


async def _add_machines_to_planning(
    db: AsyncSession, planning_id: int, machine_ids: list, now: datetime
) -> list:
    """Insert PlanningMachines rows; return sorted deduped id list."""
    deduped = sorted(set(machine_ids))
    for machine_id in deduped:
        db.add(PlanningMachines(planning_id=planning_id, machine_id=machine_id, created_at=now))
    await db.commit()
    return deduped


async def _validate_shift_compatibility(
    db: AsyncSession, all_assigned_users: list, shift_type: str | None, planning_type: str
) -> None:
    """Raise 400 when any assigned user has a mismatched shift_type for SHIFT plannings."""
    if planning_type != PlanningType.SHIFT.value or not shift_type or not all_assigned_users:
        return
    mismatched_result = await db.execute(
        select(Utilisateurs.id)
        .where(Utilisateurs.id.in_(all_assigned_users))
        .where(Utilisateurs.shift_type != shift_type)
    )
    mismatched_ids = [row[0] for row in mismatched_result.fetchall()]
    if mismatched_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Users {mismatched_ids} do not match planning shift_type {shift_type}",
        )


async def _send_user_notifications(
    db: AsyncSession,
    planning_id: int,
    identifiant: str,
    planning_response_data: dict,
    all_assigned_users: list,
) -> None:
    """Send in-app + email notifications to assigned users (no-op when list is empty)."""
    if not all_assigned_users:
        return
    await send_planning_notifications(db, planning_id, identifiant, all_assigned_users)
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


@router.post("", response_model=PlanningResponse, status_code=status.HTTP_201_CREATED, responses={400: {"description": "Failed to create planning"}, 500: {"description": "Internal Server Error"}})
async def create_planning(
    data: PlanningCreateData,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new planning (admin only)"""
    verify_admin(current_user)
    safe_technicien_ids = repr(data.technicien_ids)
    logger.info(f"CREATE planning — technicien_ids received: {safe_technicien_ids}")

    try:
        # Create planning directly without service to avoid greenlet_spawn
        planning_statut_value = _resolve_planning_statut(data.planning_statut)

        planning_data = {
            "identifiant_planning": data.identifiant_planning,
            "date_debut": data.date_debut,
            "date_fin": data.date_fin,
            "type": data.type,
            "shift_type": data.shift_type,
            "chef_operation_id": data.chef_operation_id,
            "chef_technique_id": data.chef_technique_id,
            "zone_travail": data.zone_travail,
            "planning_statut": planning_statut_value,
            "created_at": datetime.now(),
        }

        planning = Plannings(**planning_data)
        db.add(planning)
        await db.commit()
        await db.refresh(planning)

        if not planning:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create planning",
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
            "planning_statut": planning_statut_value.value
            if hasattr(planning_statut_value, "value")
            else str(planning_statut_value),
            "chef_operation_id": data.chef_operation_id,
            "chef_technique_id": data.chef_technique_id,
            "zone_travail": data.zone_travail,
            "created_at": datetime.now(),
            "assigned_users": [],
            "machine_ids": [],
        }

        if data.machine_ids:
            planning_response_data["machine_ids"] = await _add_machines_to_planning(
                db, planning_id, data.machine_ids, datetime.now()
            )

        # Assign users (dedupe + shift validation)
        all_assigned_users = _collect_user_ids(data)
        await _validate_shift_compatibility(db, all_assigned_users, data.shift_type, data.type)

        now = datetime.now()
        for user_id in all_assigned_users:
            db.add(
                PlanningUtilisateurs(
                    planning_id=planning_id,
                    utilisateur_id=user_id,
                    created_at=now,
                )
            )
        await db.commit()

        await _send_user_notifications(
            db, planning_id, data.identifiant_planning, planning_response_data, all_assigned_users
        )

        # Fetch assigned users and machines using helper function for accurate response
        fresh_planning = await PlanningsService(db).get_by_id(planning_id)
        planning_response_data = await get_planning_with_users(db, fresh_planning)

        try:
            await AuditService(db).log_create(
                entity_type=AuditEntityType.PLANNING,
                entity_id=planning_id,
                new_values={
                    "identifiant_planning": data.identifiant_planning,
                    "type": data.type,
                    "date_debut": str(data.date_debut),
                    "date_fin": str(data.date_fin),
                },
                user_id=current_user.id,
                user_name=current_user.nom,
                entity_name=data.identifiant_planning,
            )
        except Exception:
            logger.warning("Audit log failed for create planning %s", planning_id)

        return planning_response_data

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error creating planning: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create planning: {str(e)}",
        )


@router.post("/{planning_id}/resend-emails", responses={404: {"description": "Planning not found"}})
async def resend_planning_emails(
    planning_id: int,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Manually re-send planning assignment emails to currently assigned users (admin only)."""
    verify_admin(current_user)

    service = PlanningsService(db)
    planning = await service.get_by_id(planning_id)
    if not planning:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=_PLANNING_NOT_FOUND_MSG
        )

    assigned_ids_result = await db.execute(
        select(PlanningUtilisateurs.utilisateur_id).where(
            PlanningUtilisateurs.planning_id == planning_id
        )
    )
    user_ids = [row[0] for row in assigned_ids_result.fetchall()]

    if not user_ids:
        return {"queued": 0}

    users_result = await db.execute(
        select(Utilisateurs).where(Utilisateurs.id.in_(user_ids))
    )
    users = users_result.scalars().all()
    recipients = [
        {"id": u.id, "nom": u.nom, "email": u.email}
        for u in users
        if getattr(u, "email", None)
    ]
    if not recipients:
        return {"queued": 0}

    planning_payload = _serialize_planning_for_email(
        {
            "id": planning.id,
            "identifiant_planning": planning.identifiant_planning,
            "date_debut": planning.date_debut,
            "date_fin": planning.date_fin,
            "type": planning.type.value if getattr(planning, "type", None) else "",
            "shift_type": planning.shift_type.value
            if getattr(planning, "shift_type", None)
            else None,
            "zone_travail": getattr(planning, "zone_travail", None),
        }
    )

    send_planning_assignment_emails.delay(recipients, planning_payload)
    return {"queued": len(recipients)}


@router.delete("/{planning_id}", responses={404: {"description": "Planning not found"}, 500: {"description": "Internal Server Error"}})
async def delete_planning(
    planning_id: int,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a planning (admin only)"""
    verify_admin(current_user)

    try:
        # Delete associated PlanningUtilisateurs records first
        pu_service = PlanningUtilisateursService(db)
        result = await db.execute(
            select(PlanningUtilisateurs).where(
                PlanningUtilisateurs.planning_id == planning_id
            )
        )
        assignments = result.scalars().all()

        for assignment in assignments:
            await pu_service.delete(assignment.id)

        # Delete planning
        service = PlanningsService(db)
        success = await service.delete(planning_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=_PLANNING_NOT_FOUND_MSG
            )

        try:
            await AuditService(db).log_delete(
                entity_type=AuditEntityType.PLANNING,
                entity_id=planning_id,
                user_id=current_user.id,
                user_name=current_user.nom,
            )
        except Exception:
            logger.warning("Audit log failed for delete planning %s", planning_id)

        return {"message": "Planning deleted successfully", "id": planning_id}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(
            f"Error deleting planning {planning_id}: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete planning: {str(e)}",
        )


# Planning workflow endpoints: Submit (CHEFTECH) and Approve/Reject (ADMIN)


@router.post("/{planning_id}/submit", responses={404: {"description": "Planning not found"}})
async def submit_planning(
    planning_id: int,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Submit a planning for approval (CHEFTECH only)"""
    verify_cheftech(current_user)
    service = PlanningsService(db)
    planning = await service.get_by_id(planning_id)
    if not planning:
        raise HTTPException(status_code=404, detail=_PLANNING_NOT_FOUND_MSG)

    # Update status to SUBMITTED
    await service.update(planning_id, {"planning_statut": PlanningStatut.SUBMITTED})

    try:
        await AuditService(db).log_update(
            entity_type=AuditEntityType.PLANNING,
            entity_id=planning_id,
            old_values={
                "planning_statut": planning.planning_statut.value
                if planning.planning_statut
                else "DRAFT"
            },
            new_values={"planning_statut": "SUBMITTED"},
            user_id=current_user.id,
            user_name=current_user.nom,
            entity_name=planning.identifiant_planning,
        )
    except Exception:
        logger.warning("Audit log failed for submit planning %s", planning_id)

    return {
        "message": "Planning submitted for approval",
        "id": planning_id,
        "planning_statut": "SUBMITTED",
    }


@router.post("/{planning_id}/approve", responses={404: {"description": "Planning not found"}})
async def approve_planning(
    planning_id: int,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Approve a planning (ADMIN only)"""
    verify_admin(current_user)
    service = PlanningsService(db)
    planning = await service.get_by_id(planning_id)
    if not planning:
        raise HTTPException(status_code=404, detail=_PLANNING_NOT_FOUND_MSG)

    # Update status to APPROVED
    await service.update(planning_id, {"planning_statut": PlanningStatut.APPROVED})

    try:
        await AuditService(db).log_update(
            entity_type=AuditEntityType.PLANNING,
            entity_id=planning_id,
            old_values={
                "planning_statut": planning.planning_statut.value
                if planning.planning_statut
                else "SUBMITTED"
            },
            new_values={"planning_statut": "APPROVED"},
            user_id=current_user.id,
            user_name=current_user.nom,
            entity_name=planning.identifiant_planning,
        )
    except Exception:
        logger.warning("Audit log failed for approve planning %s", planning_id)

    return {
        "message": "Planning approved",
        "id": planning_id,
        "planning_statut": "APPROVED",
    }


@router.post("/{planning_id}/reject", responses={404: {"description": "Planning not found"}})
async def reject_planning(
    planning_id: int,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Reject a planning (ADMIN only)"""
    verify_admin(current_user)
    service = PlanningsService(db)
    planning = await service.get_by_id(planning_id)
    if not planning:
        raise HTTPException(status_code=404, detail=_PLANNING_NOT_FOUND_MSG)

    # Update status to REJECTED
    await service.update(planning_id, {"planning_statut": PlanningStatut.REJECTED})

    try:
        await AuditService(db).log_update(
            entity_type=AuditEntityType.PLANNING,
            entity_id=planning_id,
            old_values={
                "planning_statut": planning.planning_statut.value
                if planning.planning_statut
                else "SUBMITTED"
            },
            new_values={"planning_statut": "REJECTED"},
            user_id=current_user.id,
            user_name=current_user.nom,
            entity_name=planning.identifiant_planning,
        )
    except Exception:
        logger.warning("Audit log failed for reject planning %s", planning_id)

    return {
        "message": "Planning rejected",
        "id": planning_id,
        "planning_statut": "REJECTED",
    }

