"""Required-pieces router — attach planned pieces to an intervention.

Called by the intervention-request flow (frontend `PiecePicker`). Each row
becomes a reservation candidate when the CHEFTECH approves the intervention.
"""

import logging
from decimal import Decimal
from typing import List, Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.auth import require_role
from models.ordres_intervention import OrdresIntervention
from models.pieces import Piece
from models.required_pieces import RequiredPiece
from models.utilisateurs import Utilisateurs
from schemas.stock import RequiredPieceItem, RequiredPieceResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/inventory/required-pieces", tags=["inventory-required"]
)

_INTERNAL_SERVER_ERROR_MSG = "Internal server error"

ROLES_ATTACH = ["TECHNICIEN", "CHEFTECH", "CHETOP", "ADMIN"]


@router.post(
    "/{intervention_id}",
    response_model=List[RequiredPieceResponse],
    status_code=201, responses={400: {"description": "At most 100 required pieces per request"}, 404: {"description": "Intervention not found"}, 500: {"description": "Internal server error"}})
async def attach_required_pieces(
    intervention_id: int,
    items: List[RequiredPieceItem],
    current_user: Annotated[Utilisateurs, Depends(require_role(ROLES_ATTACH))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Attach a list of required pieces to an intervention.

    - Verifies intervention exists
    - Verifies every piece_id exists
    - Inserts RequiredPiece rows with approved=NULL (pending CHEFTECH approval)
    - Returns the inserted rows with piece names attached
    """
    if not items:
        return []
    if len(items) > 100:
        raise HTTPException(
            status_code=400, detail="At most 100 required pieces per request"
        )

    try:
        # Validate intervention
        intervention = await db.scalar(
            select(OrdresIntervention).where(OrdresIntervention.id == intervention_id)
        )
        if intervention is None:
            raise HTTPException(status_code=404, detail="Intervention not found")

        # Validate piece IDs and gather unit defaults
        piece_ids = list({i.piece_id for i in items})
        pieces = (
            (await db.execute(select(Piece).where(Piece.id.in_(piece_ids))))
            .scalars()
            .all()
        )
        pieces_by_id = {p.id: p for p in pieces}
        missing = [pid for pid in piece_ids if pid not in pieces_by_id]
        if missing:
            raise HTTPException(status_code=404, detail=f"Pieces not found: {missing}")

        # Insert
        created: List[RequiredPiece] = []
        for item in items:
            piece = pieces_by_id[item.piece_id]
            unit = item.unit or piece.default_unit or "pcs"
            row = RequiredPiece(
                intervention_id=intervention_id,
                piece_id=item.piece_id,
                quantity_planned=item.quantity_planned,
                unit=unit,
                quantity_reserved=Decimal(0),
                approved=None,
            )
            db.add(row)
            created.append(row)

        await db.commit()
        for r in created:
            await db.refresh(r)

        return [
            RequiredPieceResponse(
                id=r.id,
                intervention_id=r.intervention_id,
                piece_id=r.piece_id,
                piece_name=pieces_by_id[r.piece_id].name,
                piece_reference=pieces_by_id[r.piece_id].reference,
                quantity_planned=r.quantity_planned,
                unit=r.unit,
                quantity_reserved=r.quantity_reserved,
                reservation_expires_at=r.reservation_expires_at,
                approved=r.approved,
                created_at=r.created_at,
            )
            for r in created
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"attach_required_pieces failed for itv {intervention_id}: {e}",
            exc_info=True,
        )
        await db.rollback()
        raise HTTPException(status_code=500, detail=_INTERNAL_SERVER_ERROR_MSG)


@router.get("/{intervention_id}", response_model=List[RequiredPieceResponse], responses={500: {"description": "Internal server error"}})
async def list_required_pieces(
    intervention_id: int,
    current_user: Annotated[Utilisateurs, Depends(require_role(ROLES_ATTACH))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List required pieces for an intervention with piece-name join."""
    try:
        rows = (
            await db.execute(
                select(RequiredPiece, Piece)
                .join(Piece, Piece.id == RequiredPiece.piece_id)
                .where(RequiredPiece.intervention_id == intervention_id)
                .order_by(RequiredPiece.id)
            )
        ).all()
        return [
            RequiredPieceResponse(
                id=rp.id,
                intervention_id=rp.intervention_id,
                piece_id=rp.piece_id,
                piece_name=p.name,
                piece_reference=p.reference,
                quantity_planned=rp.quantity_planned,
                unit=rp.unit,
                quantity_reserved=rp.quantity_reserved,
                reservation_expires_at=rp.reservation_expires_at,
                approved=rp.approved,
                created_at=rp.created_at,
            )
            for rp, p in rows
        ]
    except Exception as e:
        logger.exception(f"list_required_pieces failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=_INTERNAL_SERVER_ERROR_MSG)


@router.delete("/{intervention_id}/{required_piece_id}", status_code=204, responses={400: {"description": "Cannot remove reserved required piece — release first"}, 404: {"description": "Required piece not found"}, 500: {"description": "Internal server error"}})
async def remove_required_piece(
    intervention_id: int,
    required_piece_id: int,
    current_user: Annotated[Utilisateurs, Depends(require_role(ROLES_ATTACH))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Remove a not-yet-reserved required piece (e.g. user mistake in picker)."""
    try:
        rp = await db.scalar(
            select(RequiredPiece).where(
                RequiredPiece.id == required_piece_id,
                RequiredPiece.intervention_id == intervention_id,
            )
        )
        if rp is None:
            raise HTTPException(status_code=404, detail="Required piece not found")
        if Decimal(str(rp.quantity_reserved)) > 0:
            raise HTTPException(
                status_code=400,
                detail="Cannot remove reserved required piece — release first",
            )
        await db.delete(rp)
        await db.commit()
        return
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(f"remove_required_piece failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=_INTERNAL_SERVER_ERROR_MSG)
