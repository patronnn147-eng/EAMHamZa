"""Admin User Management Routes"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_db
from models.utilisateurs import Utilisateurs, UserRole, UserShiftType, UserStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/users", tags=["admin-users"])


class AdminUserResponse(BaseModel):
    id: int
    nom: str
    email: str
    role: str
    status: str
    shift_type: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AdminUsersListResponse(BaseModel):
    items: List[AdminUserResponse]
    total: int


class UpdateUserStatusRequest(BaseModel):
    status: UserStatus


class UpdateUserShiftRequest(BaseModel):
    shift_type: UserShiftType


async def _require_admin(current_user: Utilisateurs) -> None:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can perform this action",
        )


@router.get("", response_model=AdminUsersListResponse)
async def list_users(
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_admin(current_user)

    result = await db.execute(select(Utilisateurs).order_by(Utilisateurs.id.desc()))
    users = result.scalars().all()

    items = [
        AdminUserResponse(
            id=u.id,
            nom=u.nom,
            email=u.email,
            role=u.role.value if hasattr(u.role, "value") else str(u.role),
            status=u.status.value if hasattr(u.status, "value") else str(u.status),
            shift_type=u.shift_type.value if hasattr(u.shift_type, "value") else (str(u.shift_type) if u.shift_type else None),
            created_at=u.created_at,
            updated_at=u.updated_at,
        )
        for u in users
    ]

    return AdminUsersListResponse(items=items, total=len(items))


@router.patch("/{user_id}/status", response_model=AdminUserResponse)
async def update_user_status(
    user_id: int,
    data: UpdateUserStatusRequest,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_admin(current_user)

    result = await db.execute(select(Utilisateurs).where(Utilisateurs.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.status = data.status
    user.updated_at = datetime.now()
    await db.commit()
    await db.refresh(user)

    return AdminUserResponse(
        id=user.id,
        nom=user.nom,
        email=user.email,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        status=user.status.value if hasattr(user.status, "value") else str(user.status),
        shift_type=user.shift_type.value if hasattr(user.shift_type, "value") else (str(user.shift_type) if user.shift_type else None),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.patch("/{user_id}/shift-type", response_model=AdminUserResponse)
async def update_user_shift_type(
    user_id: int,
    data: UpdateUserShiftRequest,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_admin(current_user)

    result = await db.execute(select(Utilisateurs).where(Utilisateurs.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.shift_type = data.shift_type
    user.updated_at = datetime.now()
    await db.commit()
    await db.refresh(user)

    return AdminUserResponse(
        id=user.id,
        nom=user.nom,
        email=user.email,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        status=user.status.value if hasattr(user.status, "value") else str(user.status),
        shift_type=user.shift_type.value if hasattr(user.shift_type, "value") else (str(user.shift_type) if user.shift_type else None),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_admin(current_user)

    if current_user.id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account")

    result = await db.execute(select(Utilisateurs).where(Utilisateurs.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await db.delete(user)
    await db.commit()

    return {"message": "User deleted successfully", "id": user_id}
