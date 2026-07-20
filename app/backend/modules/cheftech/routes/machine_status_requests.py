from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.utilisateurs import Utilisateurs
from modules.cheftech.dependencies import verify_cheftech_only
from modules.shared.services.machine_status_requests import (
    approve_status_change_request,
    list_pending_requests,
    reject_status_change_request,
)

router = APIRouter(prefix="/api/v1/cheftech", tags=["cheftech"])


class RejectPayload(BaseModel):
    note: Optional[str] = None


@router.get("/machine-status-requests")
async def get_pending_machine_status_requests(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[Utilisateurs, Depends(verify_cheftech_only)],
) -> dict:
    """CHEFTECH: list technician-proposed machine status changes awaiting review."""
    items = await list_pending_requests(db)
    return {"pending_count": len(items), "items": items}


@router.patch(
    "/machine-status-requests/{request_id}/approve",
    responses={404: {"description": "Request not found"}, 400: {"description": "Request is not pending"}},
)
async def approve_machine_status_request(
    request_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(verify_cheftech_only)],
) -> dict:
    """CHEFTECH: approve a proposed status change. Sets Machines.statut."""
    result = await approve_status_change_request(
        request_id, current_user.id, db, approved_by_name=current_user.nom
    )
    if not result["success"]:
        status_code = 404 if result["error"] == "Request not found" else 400
        raise HTTPException(status_code=status_code, detail=result["error"])
    return result


@router.patch(
    "/machine-status-requests/{request_id}/reject",
    responses={404: {"description": "Request not found"}, 400: {"description": "Request is not pending"}},
)
async def reject_machine_status_request(
    request_id: int,
    payload: RejectPayload,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(verify_cheftech_only)],
) -> dict:
    """CHEFTECH: reject a proposed status change. Machines.statut unchanged."""
    result = await reject_status_change_request(
        request_id, current_user.id, payload.note, db, rejected_by_name=current_user.nom
    )
    if not result["success"]:
        status_code = 404 if result["error"] == "Request not found" else 400
        raise HTTPException(status_code=status_code, detail=result["error"])
    return result
