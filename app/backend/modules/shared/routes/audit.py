import logging
from typing import Optional, Annotated
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs, UserRole
from services.audit import AuditService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


class AuditLogResponse(BaseModel):
    id: int
    action_type: str
    entity_type: str
    entity_id: int
    entity_name: Optional[str] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    changes: Optional[dict] = None
    old_values: Optional[dict] = None
    new_values: Optional[dict] = None
    ip_address: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditStatsResponse(BaseModel):
    by_action: dict
    by_user: dict
    by_entity: dict
    total: int


@router.get("/log", response_model=dict, responses={403: {"description": "Only admin can view audit logs"}})
async def get_audit_log(
    *, entity_type: Annotated[Optional[str], Query(description="Filter by entity type")] = None,
    entity_id: Annotated[Optional[int], Query(description="Filter by entity ID")] = None,
    user_id: Annotated[Optional[int], Query(description="Filter by user ID")] = None,
    action_type: Annotated[Optional[str], Query(description="Filter by action type")] = None,
    user_search: Annotated[Optional[str], Query(description="Search by user name")] = None,
    from_date: Annotated[Optional[datetime], Query(description="From date")] = None,
    to_date: Annotated[Optional[datetime], Query(description="To date")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Get audit log entries with filters"""
    if current_user.role not in [UserRole.ADMIN, UserRole.CHEFTECH]:
        raise HTTPException(status_code=403, detail="Only admin can view audit logs")

    service = AuditService(db)
    result = await service.get_audit_log(
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        action_type=action_type,
        user_role=current_user.role,
        user_search=user_search,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit,
    )

    items = [
        {
            "id": item.id,
            "action_type": item.action_type.value
            if item.action_type
            else item.action_type,
            "entity_type": item.entity_type.value
            if item.entity_type
            else item.entity_type,
            "entity_id": item.entity_id,
            "entity_name": item.entity_name,
            "user_id": item.user_id,
            "user_name": item.user_name,
            "changes": item.changes,
            "old_values": item.old_values,
            "new_values": item.new_values,
            "ip_address": item.ip_address,
            "description": item.description,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in result["items"]
    ]

    return {
        "items": items,
        "total": result["total"],
        "skip": result["skip"],
        "limit": result["limit"],
    }


@router.get("/log/{entity_type}/{entity_id}", response_model=list)
async def get_entity_history(
    *, entity_type: str,
    entity_id: int,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Get complete history for a specific entity"""
    service = AuditService(db)
    history = await service.get_entity_history(entity_type, entity_id, limit)

    return [
        {
            "id": item.id,
            "action_type": item.action_type.value
            if item.action_type
            else item.action_type,
            "entity_type": item.entity_type.value
            if item.entity_type
            else item.entity_type,
            "entity_id": item.entity_id,
            "entity_name": item.entity_name,
            "user_id": item.user_id,
            "user_name": item.user_name,
            "changes": item.changes,
            "old_values": item.old_values,
            "new_values": item.new_values,
            "description": item.description,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in history
    ]


@router.get("/stats", response_model=AuditStatsResponse, responses={403: {"description": "Only admin can view audit stats"}})
async def get_audit_stats(
    *, entity_type: Annotated[Optional[str], Query(description="Filter by entity type")] = None,
    entity_id: Annotated[Optional[int], Query(description="Filter by entity ID")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Get audit log statistics"""
    if current_user.role not in [UserRole.ADMIN, UserRole.CHEFTECH]:
        raise HTTPException(status_code=403, detail="Only admin can view audit stats")

    service = AuditService(db)
    stats = await service.get_audit_stats(entity_type, entity_id)
    return stats


@router.get("/export", responses={403: {"description": "Only admin or cheftech can export audit logs"}})
async def export_audit_log(
    *, entity_type: Annotated[Optional[str], Query()] = None,
    from_date: Annotated[Optional[datetime], Query()] = None,
    to_date: Annotated[Optional[datetime], Query()] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """Export audit log to CSV"""
    if current_user.role not in (UserRole.ADMIN, UserRole.CHEFTECH):
        raise HTTPException(
            status_code=403, detail="Only admin or cheftech can export audit logs"
        )

    service = AuditService(db)
    result = await service.get_audit_log(
        entity_type=entity_type,
        user_role=current_user.role,
        from_date=from_date,
        to_date=to_date,
        skip=0,
        limit=10000,
    )

    csv_lines = [
        "id,action_type,entity_type,entity_id,user_name,description,created_at"
    ]
    for item in result["items"]:
        csv_lines.append(
            f"{item.id},"
            f"{item.action_type.value if item.action_type else ''},"
            f"{item.entity_type.value if item.entity_type else ''},"
            f"{item.entity_id},"
            f"{item.user_name or ''},"
            f"{(item.description or '').replace(',', ';')},"
            f"{item.created_at.isoformat() if item.created_at else ''}"
        )

    return {"csv": "\n".join(csv_lines), "count": result["total"]}
