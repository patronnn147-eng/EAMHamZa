"""Intervention parts detail endpoint.

Single GET that surfaces everything the frontend needs to render an
intervention's parts panel:
- required_pieces (planned + reserved status)
- consumed_pieces (actual usage)
- pending_pieces (uncatalogued items linked to this intervention)
- aggregate parts_replaced JSON (from the view)
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.auth import require_role
from models.consumed_pieces import ConsumedPiece
from models.ordres_intervention import Ordres_intervention
from models.pending_pieces import PendingPiece
from models.pieces import Piece
from models.required_pieces import RequiredPiece
from models.utilisateurs import Utilisateurs

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/inventory/intervention", tags=["inventory-intervention"]
)

ROLES_READ = ["TECHNICIEN", "CHEFTECH", "CHETOP", "ADMIN"]


@router.get("/{intervention_id}/parts", response_model=Dict[str, Any])
async def get_intervention_parts(
    intervention_id: int,
    _u: Utilisateurs = Depends(require_role(ROLES_READ)),
    db: AsyncSession = Depends(get_db),
):
    """Return all pieces-related data for an intervention in one payload."""
    # Verify intervention exists
    itv = await db.scalar(
        select(Ordres_intervention).where(Ordres_intervention.id == intervention_id)
    )
    if itv is None:
        raise HTTPException(status_code=404, detail="Intervention not found")

    try:
        # Required pieces
        required_rows = (
            await db.execute(
                select(RequiredPiece, Piece.name, Piece.reference, Piece.default_unit)
                .join(Piece, Piece.id == RequiredPiece.piece_id)
                .where(RequiredPiece.intervention_id == intervention_id)
                .order_by(RequiredPiece.id)
            )
        ).all()
        required = [
            {
                "id": rp.id,
                "piece_id": rp.piece_id,
                "piece_name": name,
                "piece_reference": ref,
                "quantity_planned": str(rp.quantity_planned),
                "unit": rp.unit or default_unit or "pcs",
                "quantity_reserved": str(rp.quantity_reserved),
                "reservation_expires_at": rp.reservation_expires_at.isoformat()
                if rp.reservation_expires_at
                else None,
                "approved": rp.approved,
                "created_at": rp.created_at.isoformat() if rp.created_at else None,
            }
            for rp, name, ref, default_unit in required_rows
        ]

        # Consumed pieces
        consumed_rows = (
            await db.execute(
                select(ConsumedPiece, Piece.name, Piece.reference)
                .join(Piece, Piece.id == ConsumedPiece.piece_id)
                .where(ConsumedPiece.intervention_id == intervention_id)
                .order_by(ConsumedPiece.id)
            )
        ).all()
        consumed = [
            {
                "id": cp.id,
                "required_piece_id": cp.required_piece_id,
                "piece_id": cp.piece_id,
                "piece_name": name,
                "piece_reference": ref,
                "quantity_used": str(cp.quantity_used),
                "quantity_returned": str(cp.quantity_returned),
                "quantity_wasted": str(cp.quantity_wasted),
                "unit": cp.unit,
                "disposition": cp.disposition,
                "notes": cp.notes,
                "created_at": cp.created_at.isoformat() if cp.created_at else None,
            }
            for cp, name, ref in consumed_rows
        ]

        # Pending pieces
        pending_rows = (
            await db.execute(
                select(PendingPiece, Piece.name.label("matched_name"))
                .outerjoin(Piece, Piece.id == PendingPiece.matched_piece_id)
                .where(PendingPiece.intervention_id == intervention_id)
                .order_by(PendingPiece.id)
            )
        ).all()
        pending = [
            {
                "id": pp.id,
                "name": pp.name,
                "category": pp.category,
                "quantity": str(pp.quantity),
                "unit": pp.unit,
                "photo_object_key": pp.photo_object_key,
                "notes": pp.notes,
                "status": pp.status,
                "matched_piece_id": pp.matched_piece_id,
                "matched_piece_name": matched_name,
                "rejection_reason": pp.rejection_reason,
                "created_at": pp.created_at.isoformat() if pp.created_at else None,
            }
            for pp, matched_name in pending_rows
        ]

        # Aggregate summary from the VIEW (single source of truth)
        summary_row = (
            await db.execute(
                text(
                    "SELECT parts_replaced_json FROM intervention_consumption_summary WHERE intervention_id = :iid"
                ),
                {"iid": intervention_id},
            )
        ).first()
        parts_replaced_json = summary_row[0] if summary_row else None

        return {
            "intervention_id": intervention_id,
            "parts_approved": itv.parts_approved,
            "required": required,
            "consumed": consumed,
            "pending": pending,
            "parts_replaced_json": parts_replaced_json,
        }
    except Exception as e:
        logger.error(
            f"get_intervention_parts failed for itv {intervention_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/by-wo/{work_order_id}/parts", response_model=Dict[str, Any])
async def get_parts_by_work_order(
    work_order_id: int,
    _u: Utilisateurs = Depends(require_role(ROLES_READ)),
    db: AsyncSession = Depends(get_db),
):
    """Same payload as `/intervention/{id}/parts` but keyed by work_order_id."""
    itv_id = await db.scalar(
        select(Ordres_intervention.id).where(
            Ordres_intervention.ordre_travail_id == work_order_id
        )
    )
    if itv_id is None:
        # No linked intervention — return empty shell so UI can degrade gracefully
        return {
            "intervention_id": None,
            "parts_approved": None,
            "required": [],
            "consumed": [],
            "pending": [],
            "parts_replaced_json": None,
        }
    return await get_intervention_parts(itv_id, _u=_u, db=db)
