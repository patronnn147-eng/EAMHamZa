import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs, UserRole
from services.audit import AuditService, AuditActionType, AuditEntityType, AuditLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


class AuditLogResponse(BaseModel):
    id: int
    action_type: str
    entity_type: str
    entity_id: int
    entity_name: Optional[str]
    user_id: Optional[int]
    user_name: Optional[str]
    changes: Optional[dict]
    old_values: Optional[dict]
    new_values: Optional[dict]
    ip_address: Optional[str]
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AuditStatsResponse(BaseModel):
    by_action: dict
    by_user: dict
    by_entity: dict
    total: int


@router.get("/log", response_model=dict)
async def get_audit_log(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_id: Optional[int] = Query(None, description="Filter by entity ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    from_date: Optional[datetime] = Query(None, description="From date"),
    to_date: Optional[datetime] = Query(None, description="To date"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
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
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit,
    )
    
    items = [
        {
            "id": item.id,
            "action_type": item.action_type.value if item.action_type else item.action_type,
            "entity_type": item.entity_type.value if item.entity_type else item.entity_type,
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
    entity_type: str,
    entity_id: int,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Get complete history for a specific entity"""
    service = AuditService(db)
    history = await service.get_entity_history(entity_type, entity_id, limit)
    
    return [
        {
            "id": item.id,
            "action_type": item.action_type.value if item.action_type else item.action_type,
            "entity_type": item.entity_type.value if item.entity_type else item.entity_type,
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


@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_stats(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_id: Optional[int] = Query(None, description="Filter by entity ID"),
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Get audit log statistics"""
    if current_user.role not in [UserRole.ADMIN, UserRole.CHEFTECH]:
        raise HTTPException(status_code=403, detail="Only admin can view audit stats")
    
    service = AuditService(db)
    stats = await service.get_audit_stats(entity_type, entity_id)
    return stats


@router.get("/export")
async def export_audit_log(
    entity_type: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Export audit log to CSV"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admin can export audit logs")
    
    service = AuditService(db)
    result = await service.get_audit_log(
        entity_type=entity_type,
        from_date=from_date,
        to_date=to_date,
        skip=0,
        limit=10000,
    )
    
    csv_lines = ["id,action_type,entity_type,entity_id,user_name,description,created_at"]
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
