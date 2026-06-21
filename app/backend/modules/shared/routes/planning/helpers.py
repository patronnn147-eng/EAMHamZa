import logging
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.utilisateurs import Utilisateurs, UserRole
from models.plannings import Plannings, PlanningType
from models.planning_machines import Planning_machines
from models.planning_utilisateurs import Planning_utilisateurs
from services.notifications import NotificationsService

logger = logging.getLogger(__name__)


def _serialize_planning_for_email(payload: dict) -> dict:
    def _dt(value: object) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        return "" if value is None else str(value)

    return {
        "id": payload.get("id"),
        "identifiant_planning": payload.get("identifiant_planning", ""),
        "date_debut": _dt(payload.get("date_debut")),
        "date_fin": _dt(payload.get("date_fin")),
        "type": payload.get("type", ""),
        "shift_type": payload.get("shift_type") or "",
        "zone_travail": payload.get("zone_travail") or "",
    }


async def verify_admin(current_user: Utilisateurs):
    """Verify that the current user is an admin"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'avez pas la permission pour cette action",
        )


async def verify_cheftech(current_user: Utilisateurs):
    """Verify that the current user is a CHEFTECH"""
    if current_user.role != UserRole.CHEFTECH:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'avez pas la permission pour cette action",
        )


async def verify_chetop_or_cheftech(current_user: Utilisateurs):
    """Verify that the current user is CHETOP or CHEFTECH"""
    if current_user.role not in [UserRole.CHETOP, UserRole.CHEFTECH]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'avez pas la permission pour cette action",
        )


async def verify_cheftech_or_tech(current_user: Utilisateurs):
    """Verify that the current user is CHEFTECH or TECHNICIEN"""
    if current_user.role not in [UserRole.CHEFTECH, UserRole.TECHNICIEN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'avez pas la permission pour cette action",
        )


async def verify_any_role(current_user: Utilisateurs):
    """Verify that the user has any of the defined roles"""
    # All users have some role, this always passes
    pass


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[Utilisateurs]:
    """Get user by ID"""
    result = await db.execute(select(Utilisateurs).where(Utilisateurs.id == user_id))
    return result.scalar_one_or_none()


async def validate_planning_data(db: AsyncSession, data):
    """Validate planning data"""
    # Validate shift_type is provided only for SHIFT type
    if data.type == PlanningType.SHIFT:
        if not data.shift_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="shift_type is required for SHIFT planning",
            )
        if not data.chef_operation_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="chef_operation_id is required for SHIFT planning",
            )
    elif data.shift_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="shift_type should only be provided for SHIFT planning",
        )

    # Validate chef_operation exists and has CHETOP role
    if data.chef_operation_id:
        chef_op = await get_user_by_id(db, data.chef_operation_id)
        if not chef_op:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chef Operation with ID {data.chef_operation_id} not found",
            )
        if chef_op.role != UserRole.CHETOP:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chef Operation must have CHETOP role",
            )

    # Validate chef_technique exists and has CHEFTECH role
    if data.chef_technique_id:
        chef_tech = await get_user_by_id(db, data.chef_technique_id)
        if not chef_tech:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chef Technique with ID {data.chef_technique_id} not found",
            )
        if chef_tech.role != UserRole.CHEFTECH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chef Technique must have CHEFTECH role",
            )

    # Validate all technicians exist and have TECHNICIEN role
    for tech_id in data.technicien_ids:
        tech = await get_user_by_id(db, tech_id)
        if not tech:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Technician with ID {tech_id} not found",
            )
        if tech.role != UserRole.TECHNICIEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User {tech_id} must have TECHNICIEN role",
            )


async def send_planning_notifications(
    db: AsyncSession, planning_id: int, identifiant_planning: str, user_ids: List[int]
):
    """Send notifications to all assigned users"""
    notification_service = NotificationsService(db)

    for user_id in user_ids:
        try:
            notification_data = {
                "utilisateur_id": user_id,
                "titre": "Planning Assignment",
                "priorite": "MOYENNE",
                "type": "PLANNING_ASSIGNMENT",
                "message": f"You have been assigned to planning: {identifiant_planning}",
                "date_envoi": datetime.now(),
                "lu": False,
            }
            await notification_service.create(notification_data)
            logger.info(
                f"Notification sent to user {user_id} for planning {planning_id}"
            )
        except Exception as e:
            logger.error(f"Failed to send notification to user {user_id}: {str(e)}")


async def get_planning_with_users(db: AsyncSession, planning: Plannings) -> dict:
    """Get planning with assigned users.
    Uses pre-loaded relationships if available (via selectinload), otherwise falls back to queries.
    """
    # Check if relationships were pre-loaded via selectinload
    pu_loaded = "planning_utilisateurs" in planning.__dict__
    pm_loaded = "planning_machines" in planning.__dict__

    assigned_users = []
    seen_user_ids = set()

    if pu_loaded:
        # Use pre-loaded data (no extra queries)
        for pu in planning.planning_utilisateurs:
            user = pu.utilisateur
            if not user or user.id in seen_user_ids:
                continue
            seen_user_ids.add(user.id)
            role_val = (
                user.role.value if hasattr(user.role, "value") else str(user.role)
            )
            shift_val = None
            if user.shift_type:
                shift_val = (
                    user.shift_type.value
                    if hasattr(user.shift_type, "value")
                    else str(user.shift_type)
                )
            assigned_users.append(
                {
                    "id": user.id,
                    "nom": user.nom,
                    "email": user.email,
                    "role": role_val,
                    "shift_type": shift_val,
                }
            )
    else:
        # Fallback: query the database (single-item endpoints)
        result = await db.execute(
            select(Planning_utilisateurs, Utilisateurs)
            .join(Utilisateurs, Planning_utilisateurs.utilisateur_id == Utilisateurs.id)
            .where(Planning_utilisateurs.planning_id == planning.id)
        )
        for pu, user in result:
            if user.id in seen_user_ids:
                continue
            seen_user_ids.add(user.id)
            role_val = (
                user.role.value if hasattr(user.role, "value") else str(user.role)
            )
            shift_val = None
            if user.shift_type:
                shift_val = (
                    user.shift_type.value
                    if hasattr(user.shift_type, "value")
                    else str(user.shift_type)
                )
            assigned_users.append(
                {
                    "id": user.id,
                    "nom": user.nom,
                    "email": user.email,
                    "role": role_val,
                    "shift_type": shift_val,
                }
            )

    # If planning_utilisateurs had no rows, recover chef users from the plannings table itself
    # (handles plannings whose bridge rows were wiped by a past bug)
    if not assigned_users:
        chef_ids = list(
            filter(None, [planning.chef_operation_id, planning.chef_technique_id])
        )
        if chef_ids:
            chefs_result = await db.execute(
                select(Utilisateurs).where(Utilisateurs.id.in_(chef_ids))
            )
            for chef in chefs_result.scalars().all():
                if chef.id in seen_user_ids:
                    continue
                seen_user_ids.add(chef.id)
                role_val = (
                    chef.role.value if hasattr(chef.role, "value") else str(chef.role)
                )
                shift_val = (
                    chef.shift_type.value
                    if getattr(chef, "shift_type", None)
                    and hasattr(chef.shift_type, "value")
                    else (
                        str(chef.shift_type)
                        if getattr(chef, "shift_type", None)
                        else None
                    )
                )
                assigned_users.append(
                    {
                        "id": chef.id,
                        "nom": chef.nom,
                        "email": chef.email,
                        "role": role_val,
                        "shift_type": shift_val,
                    }
                )

    if pm_loaded:
        machine_ids = [pm.machine_id for pm in planning.planning_machines]
    else:
        machines_result = await db.execute(
            select(Planning_machines.machine_id).where(
                Planning_machines.planning_id == planning.id
            )
        )
        machine_ids = [row[0] for row in machines_result.fetchall()]

    # Safely handle enum values for planning
    type_val = (
        planning.type.value if hasattr(planning.type, "value") else str(planning.type)
    )
    planning_shift_val = None
    if planning.shift_type:
        planning_shift_val = (
            planning.shift_type.value
            if hasattr(planning.shift_type, "value")
            else str(planning.shift_type)
        )
    planning_statut_val = None
    if planning.planning_statut:
        planning_statut_val = (
            planning.planning_statut.value
            if hasattr(planning.planning_statut, "value")
            else str(planning.planning_statut)
        )

    return {
        "id": planning.id,
        "identifiant_planning": planning.identifiant_planning,
        "date_debut": planning.date_debut,
        "date_fin": planning.date_fin,
        "type": type_val,
        "shift_type": planning_shift_val,
        "planning_statut": planning_statut_val,
        "chef_operation_id": planning.chef_operation_id,
        "chef_technique_id": planning.chef_technique_id,
        "zone_travail": planning.zone_travail,
        "created_at": planning.created_at,
        "assigned_users": assigned_users,
        "machine_ids": machine_ids,
    }
