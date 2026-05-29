"""Reservation observability + manual release endpoints (admin only)."""
import logging
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.auth import require_role
from models.pieces import Piece
from models.required_pieces import RequiredPiece
from models.utilisateurs import Utilisateurs
from services.inventory import InventoryReservationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/inventory/reservations", tags=["inventory-reservations"])

ROLES_ADMIN = ["ADMIN", "CHEFTECH"]


class ReservationRow(BaseModel):
    required_piece_id: int
    intervention_id: int
    piece_id: int
    piece_name: Optional[str] = None
    quantity_planned: Decimal
    quantity_reserved: Decimal
    unit: str
    reservation_expires_at: Optional[str] = None
    approved: Optional[bool] = None


@router.get("", response_model=List[ReservationRow])
async def list_active_reservations(
    piece_id: Optional[int] = Query(None),
    intervention_id: Optional[int] = Query(None),
    _u: Utilisateurs = Depends(require_role(ROLES_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """List active reservations (quantity_reserved > 0) — observability."""
    try:
        q = (
            select(RequiredPiece, Piece.name)
            .join(Piece, Piece.id == RequiredPiece.piece_id)
            .where(RequiredPiece.quantity_reserved > 0)
            .order_by(RequiredPiece.reservation_expires_at)
        )
        if piece_id:
            q = q.where(RequiredPiece.piece_id == piece_id)
        if intervention_id:
            q = q.where(RequiredPiece.intervention_id == intervention_id)

        rows = (await db.execute(q)).all()
        return [
            ReservationRow(
                required_piece_id=rp.id,
                intervention_id=rp.intervention_id,
                piece_id=rp.piece_id,
                piece_name=piece_name,
                quantity_planned=rp.quantity_planned,
                quantity_reserved=rp.quantity_reserved,
                unit=rp.unit,
                reservation_expires_at=rp.reservation_expires_at.isoformat() if rp.reservation_expires_at else None,
                approved=rp.approved,
            )
            for rp, piece_name in rows
        ]
    except Exception as e:
        logger.error(f"list_active_reservations failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/release/{intervention_id}", status_code=200)
async def release_intervention_reservations(
    intervention_id: int,
    reason: str = Query("manual", max_length=50),
    current_user: Utilisateurs = Depends(require_role(ROLES_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Manually release all reservations for an intervention.

    Used when a WO is cancelled outside the standard flow, or for
    operational override (e.g. emergency stock unblock).
    """
    try:
        svc = InventoryReservationService(db)
        count = await svc.release_all(intervention_id=intervention_id, reason=reason)
        return {"intervention_id": intervention_id, "released_count": count, "reason": reason}
    except Exception as e:
        logger.error(f"release_intervention_reservations failed for itv {intervention_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/release-expired", status_code=200)
async def release_expired_now(
    _u: Utilisateurs = Depends(require_role(ROLES_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Trigger the expired-reservation sweep manually (admin button).

    Same code path as the Celery beat task; useful for ops who don't want
    to wait for the hourly cron.
    """
    try:
        svc = InventoryReservationService(db)
        count = await svc.release_expired(auto_commit=True)
        return {"released_count": count}
    except Exception as e:
        logger.error(f"release_expired_now failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
