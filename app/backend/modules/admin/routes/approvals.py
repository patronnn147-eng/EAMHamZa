"""
User Approval Routes - Admin endpoints for managing user registrations
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from schemas.pagination import PaginatedResponse

from core.database import get_db
from core.email import email_service
from core.websocket import websocket_manager
from dependencies.auth import require_role
from models.utilisateurs import Utilisateurs, UserStatus, UserRole

router = APIRouter(prefix="/api/v1/user-approvals", tags=["user-approvals"])


class ApprovalAction(BaseModel):
    """Schema for approval action"""

    user_id: str
    action: str  # "approve" or "reject"


class PendingUserResponse(BaseModel):
    """Schema for pending user response"""

    id: str
    email: str
    nom: str
    role: str
    status: str
    created_at: str


@router.get("/pending", response_model=PaginatedResponse[PendingUserResponse])
async def get_pending_users(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    _current_user: Utilisateurs = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all pending user registrations (Admin only)
    """
    skip = (page - 1) * size

    # Count total
    total_result = await db.execute(
        select(func.count(Utilisateurs.id)).where(
            Utilisateurs.status == UserStatus.PENDING
        )
    )
    total = total_result.scalar() or 0

    # nosemgrep: python.fastapi.db.generic-sql-fastapi -- SQLAlchemy select() with
    # ORM column comparisons only (page/size are validated ints via Query(ge=..., le=...));
    # no raw SQL or string interpolation is built here.
    result = await db.execute(
        select(Utilisateurs)
        .where(Utilisateurs.status == UserStatus.PENDING)
        .order_by(Utilisateurs.created_at.desc())
        .offset(skip)
        .limit(size)
    )
    pending_users = result.scalars().all()

    items = [
        PendingUserResponse(
            id=str(user.id),
            email=user.email,
            nom=user.nom,
            role=user.role.value if hasattr(user.role, "value") else str(user.role),
            status=user.status.value
            if hasattr(user.status, "value")
            else str(user.status),
            created_at=user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        )
        for user in pending_users
    ]

    return PaginatedResponse.create(items=items, total=total, page=page, size=size)


@router.post("/approve/{user_id}", response_model=dict)
async def approve_user(
    user_id: str,
    _current_user: Utilisateurs = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Approve a pending user registration (Admin only)
    """
    # Find the user
    result = await db.execute(
        select(Utilisateurs).where(Utilisateurs.id == int(user_id))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé"
        )

    if user.status != UserStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet utilisateur n'est pas en attente d'approbation",
        )

    # Update user status to APPROVED
    user.status = UserStatus.APPROVED
    await db.commit()
    await db.refresh(user)

    # Send approval email
    email_service.send_approval_email(user.email, user.nom)

    # Send real-time notification via WebSocket
    await websocket_manager.send_personal_message(
        {
            "type": "account_approved",
            "message": "Votre compte a été approuvé! Vous pouvez maintenant vous connecter.",
            "timestamp": user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        },
        str(user.id),
    )

    return {
        "message": f"Utilisateur {user.nom} approuvé avec succès",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "nom": user.nom,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "status": user.status.value
            if hasattr(user.status, "value")
            else str(user.status),
        },
    }


@router.post("/reject/{user_id}", response_model=dict)
async def reject_user(
    user_id: str,
    _current_user: Utilisateurs = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Reject a pending user registration (Admin only)
    """
    # Find the user
    result = await db.execute(
        select(Utilisateurs).where(Utilisateurs.id == int(user_id))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé"
        )

    if user.status != UserStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet utilisateur n'est pas en attente d'approbation",
        )

    # Update user status to REJECTED
    user.status = UserStatus.REJECTED
    await db.commit()
    await db.refresh(user)

    # Send rejection email
    email_service.send_rejection_email(user.email, user.nom)

    # Send real-time notification via WebSocket
    await websocket_manager.send_personal_message(
        {
            "type": "account_rejected",
            "message": (
                "Votre demande d'inscription a été rejetée. "
                "Veuillez contacter un administrateur."
            ),
            "timestamp": user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        },
        str(user.id),
    )

    return {
        "message": f"Utilisateur {user.nom} rejeté",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "nom": user.nom,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "status": user.status.value
            if hasattr(user.status, "value")
            else str(user.status),
        },
    }


@router.get("/all", response_model=PaginatedResponse[PendingUserResponse])
async def get_all_users_with_status(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    _current_user: Utilisateurs = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all users with their approval status (Admin only)
    """
    skip = (page - 1) * size

    # Count total
    total_result = await db.execute(select(func.count(Utilisateurs.id)))
    total = total_result.scalar() or 0

    # nosemgrep: python.fastapi.db.generic-sql-fastapi -- SQLAlchemy select() with no
    # filters besides pagination (validated ints); no raw SQL or interpolation here.
    result = await db.execute(
        select(Utilisateurs)
        .order_by(Utilisateurs.created_at.desc())
        .offset(skip)
        .limit(size)
    )
    all_users = result.scalars().all()

    items = [
        PendingUserResponse(
            id=str(user.id),
            email=user.email,
            nom=user.nom,
            role=user.role.value if hasattr(user.role, "value") else str(user.role),
            status=user.status.value
            if hasattr(user.status, "value")
            else str(user.status),
            created_at=user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        )
        for user in all_users
    ]

    return PaginatedResponse.create(items=items, total=total, page=page, size=size)
