"""Admin User Management Routes"""

import logging
from datetime import datetime
from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.pagination import PaginatedResponse

from core.auth import get_current_user
from core.database import get_db
from models.utilisateurs import Utilisateurs, UserRole, UserShiftType, UserStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/users", tags=["admin-users"])

_USER_NOT_FOUND_MSG = "User not found"


class AdminUserResponse(BaseModel):
    id: int
    nom: str
    email: str
    role: str
    status: str
    shift_type: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# Replaced by PaginatedResponse[AdminUserResponse]


class UpdateUserStatusRequest(BaseModel):
    status: UserStatus


class UpdateUserShiftRequest(BaseModel):
    shift_type: UserShiftType


def _require_admin(current_user: Utilisateurs) -> None:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can perform this action",
        )


def _resolve_shift_type(shift_type) -> Optional[str]:
    """Normalize a shift_type value (enum or raw) into its string form."""
    if hasattr(shift_type, "value"):
        return shift_type.value
    if shift_type:
        return str(shift_type)
    return None


@router.get("", response_model=PaginatedResponse[AdminUserResponse])
async def list_users(
    *, page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 10,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    _require_admin(current_user)

    # Get total count
    total_result = await db.execute(select(func.count()).select_from(Utilisateurs))
    total_count = total_result.scalar_one()

    # Get paginated users
    skip = (page - 1) * size
    # nosemgrep: python.fastapi.db.generic-sql-fastapi -- SQLAlchemy select() with
    # ORM ordering/pagination only (validated ints); no raw SQL/string interpolation.
    result = await db.execute(
        select(Utilisateurs).order_by(Utilisateurs.id.desc()).offset(skip).limit(size)
    )
    users = result.scalars().all()

    items = [
        AdminUserResponse(
            id=u.id,
            nom=u.nom,
            email=u.email,
            role=u.role.value if hasattr(u.role, "value") else str(u.role),
            status=u.status.value if hasattr(u.status, "value") else str(u.status),
            shift_type=u.shift_type.value
            if hasattr(u.shift_type, "value")
            else (str(u.shift_type) if u.shift_type else None),
            created_at=u.created_at,
            updated_at=u.updated_at,
        )
        for u in users
    ]

    return PaginatedResponse.create(
        items=items, total=total_count, page=page, size=size
    )


@router.patch("/{user_id}/status", response_model=AdminUserResponse)
async def update_user_status(
    user_id: int,
    data: UpdateUserStatusRequest,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    _require_admin(current_user)

    result = await db.execute(select(Utilisateurs).where(Utilisateurs.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=_USER_NOT_FOUND_MSG
        )

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
        shift_type=_resolve_shift_type(user.shift_type),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.patch("/{user_id}/shift-type", response_model=AdminUserResponse)
async def update_user_shift_type(
    user_id: int,
    data: UpdateUserShiftRequest,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    _require_admin(current_user)

    result = await db.execute(select(Utilisateurs).where(Utilisateurs.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=_USER_NOT_FOUND_MSG
        )

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
        shift_type=_resolve_shift_type(user.shift_type),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    _require_admin(current_user)

    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )

    result = await db.execute(select(Utilisateurs).where(Utilisateurs.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=_USER_NOT_FOUND_MSG
        )

    await db.delete(user)
    await db.commit()

    return {"message": "User deleted successfully", "id": user_id}

