import logging
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.utilisateurs import Utilisateurs, UserRole
from models.plannings import Plannings, PlanningType
from models.planning_machines import PlanningMachines
from models.planning_utilisateurs import PlanningUtilisateurs
from services.notifications import NotificationsService

logger = logging.getLogger(__name__)

PERMISSION_DENIED_MESSAGE = "Vous n'avez pas la permission pour cette action"


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


def verify_admin(current_user: Utilisateurs):
    """Verify that the current user is an admin"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=PERMISSION_DENIED_MESSAGE,
        )


def verify_cheftech(current_user: Utilisateurs):
    """Verify that the current user is a CHEFTECH"""
    if current_user.role != UserRole.CHEFTECH:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=PERMISSION_DENIED_MESSAGE,
        )


def verify_chetop_or_cheftech(current_user: Utilisateurs):
    """Verify that the current user is CHETOP or CHEFTECH"""
    if current_user.role not in [UserRole.CHETOP, UserRole.CHEFTECH]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=PERMISSION_DENIED_MESSAGE,
        )


def verify_cheftech_or_tech(current_user: Utilisateurs):
    """Verify that the current user is CHEFTECH or TECHNICIEN"""
    if current_user.role not in [UserRole.CHEFTECH, UserRole.TECHNICIEN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=PERMISSION_DENIED_MESSAGE,
        )


async def verify_any_role(current_user: Utilisateurs):
    """Verify that the user has any of the defined roles"""
    # All users have some role, this always passes
    pass


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[Utilisateurs]:
    """Get user by ID"""
    result = await db.execute(select(Utilisateurs).where(Utilisateurs.id == user_id))
    return result.scalar_one_or_none()


def _enum_val(obj) -> Optional[str]:
    """Return obj.value for enums, str(obj) for plain values, None for None."""
    if obj is None:
        return None
    return obj.value if hasattr(obj, "value") else str(obj)


def _serialize_user(user) -> dict:
    """Return a standard user dict suitable for planning responses."""
    return {
        "id": user.id,
        "nom": user.nom,
        "email": user.email,
        "role": _enum_val(user.role),
        "shift_type": _enum_val(getattr(user, "shift_type", None)),
    }


async def _validate_shift_type_fields(data) -> None:
    """Validate shift_type / chef_operation_id consistency for SHIFT plannings."""
    if data.type == PlanningType.SHIFT:
        if not data.shift_type:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="shift_type is required for SHIFT planning")
        if not data.chef_operation_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="chef_operation_id is required for SHIFT planning")
    elif data.shift_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="shift_type should only be provided for SHIFT planning")


async def _validate_user_role(db: AsyncSession, user_id: int, expected_role: UserRole, label: str) -> None:
    """Raise 404 if user not found, 400 if role mismatch."""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"{label} with ID {user_id} not found")
    if user.role != expected_role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"{label} must have {expected_role.value} role")


async def validate_planning_data(db: AsyncSession, data):
    """Validate planning data."""
    await _validate_shift_type_fields(data)

    if data.chef_operation_id:
        await _validate_user_role(db, data.chef_operation_id, UserRole.CHETOP, "Chef Operation")

    if data.chef_technique_id:
        await _validate_user_role(db, data.chef_technique_id, UserRole.CHEFTECH, "Chef Technique")

    for tech_id in data.technicien_ids:
        await _validate_user_role(db, tech_id, UserRole.TECHNICIEN, f"User {tech_id}")


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
            logger.exception(f"Failed to send notification to user {user_id}: {str(e)}")


def _load_users_preloaded(planning) -> tuple:
    """Return (assigned_users, seen_ids) from pre-loaded PlanningUtilisateurs."""
    users, seen = [], set()
    for pu in planning.PlanningUtilisateurs:
        user = pu.utilisateur
        if not user or user.id in seen:
            continue
        seen.add(user.id)
        users.append(_serialize_user(user))
    return users, seen


async def _load_users_from_db(db: AsyncSession, planning_id: int) -> tuple:
    """Return (assigned_users, seen_ids) via DB join query."""
    result = await db.execute(
        select(PlanningUtilisateurs, Utilisateurs)
        .join(Utilisateurs, PlanningUtilisateurs.utilisateur_id == Utilisateurs.id)
        .where(PlanningUtilisateurs.planning_id == planning_id)
    )
    users, seen = [], set()
    for _pu, user in result:
        if user.id in seen:
            continue
        seen.add(user.id)
        users.append(_serialize_user(user))
    return users, seen


async def _recover_chef_users(db: AsyncSession, planning, seen_ids: set) -> list:
    """Recover chef users when bridge table has no rows (handles past-bug plannings)."""
    chef_ids = list(filter(None, [planning.chef_operation_id, planning.chef_technique_id]))
    if not chef_ids:
        return []
    result = await db.execute(select(Utilisateurs).where(Utilisateurs.id.in_(chef_ids)))
    users = []
    for chef in result.scalars().all():
        if chef.id in seen_ids:
            continue
        seen_ids.add(chef.id)
        users.append(_serialize_user(chef))
    return users


async def _get_machine_ids(db: AsyncSession, planning) -> list:
    """Return machine_ids from pre-loaded relationship or DB query."""
    if "PlanningMachines" in planning.__dict__:
        return [pm.machine_id for pm in planning.PlanningMachines]
    result = await db.execute(
        select(PlanningMachines.machine_id).where(PlanningMachines.planning_id == planning.id)
    )
    return [row[0] for row in result.fetchall()]


async def get_planning_with_users(db: AsyncSession, planning: Plannings) -> dict:
    """Get planning with assigned users.
    Uses pre-loaded relationships if available (via selectinload), otherwise falls back to queries.
    """
    if "PlanningUtilisateurs" in planning.__dict__:
        assigned_users, seen_ids = _load_users_preloaded(planning)
    else:
        assigned_users, seen_ids = await _load_users_from_db(db, planning.id)

    if not assigned_users:
        assigned_users = await _recover_chef_users(db, planning, seen_ids)

    machine_ids = await _get_machine_ids(db, planning)

    return {
        "id": planning.id,
        "identifiant_planning": planning.identifiant_planning,
        "date_debut": planning.date_debut,
        "date_fin": planning.date_fin,
        "type": _enum_val(planning.type),
        "shift_type": _enum_val(planning.shift_type),
        "planning_statut": _enum_val(planning.planning_statut),
        "chef_operation_id": planning.chef_operation_id,
        "chef_technique_id": planning.chef_technique_id,
        "zone_travail": planning.zone_travail,
        "created_at": planning.created_at,
        "assigned_users": assigned_users,
        "machine_ids": machine_ids,
    }
