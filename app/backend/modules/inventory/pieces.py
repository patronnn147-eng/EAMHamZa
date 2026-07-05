import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.inventory import PieceService
from schemas.piece import PieceCreate, PieceUpdate, PieceResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/inventory/pieces", tags=["inventory-pieces"])


# ---------- Response Schemas ----------
class PieceListResponse(BaseModel):
    items: List[PieceResponse]
    total: int
    skip: int
    limit: int


class LinkMachineRequest(BaseModel):
    machine_id: int


# ---------- Routes ----------
@router.get("", response_model=PieceListResponse)
async def list_pieces(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
):
    """List all spare parts with optional filtering and pagination."""
    service = PieceService(db)
    try:
        query_dict = None
        if query:
            try:
                query_dict = json.loads(query)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid query JSON format")

        result = await service.get_list(
            skip=skip, limit=limit, query_dict=query_dict, sort=sort
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error listing pieces: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{piece_id}", response_model=PieceResponse)
async def get_piece(piece_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single spare part by ID."""
    service = PieceService(db)
    try:
        result = await service.get_by_id(piece_id)
        if not result:
            raise HTTPException(status_code=404, detail="Piece not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching piece {piece_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=PieceResponse, status_code=201)
async def create_piece(data: PieceCreate, db: AsyncSession = Depends(get_db)):
    """Create a new spare part."""
    service = PieceService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create piece")
        safe_id = str(result.id).replace("\r", "").replace("\n", "")
        logger.info(f"Piece created with id: {safe_id}")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error creating piece: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.put("/{piece_id}", response_model=PieceResponse)
async def update_piece(
    piece_id: int, data: PieceUpdate, db: AsyncSession = Depends(get_db)
):
    """Update an existing spare part."""
    service = PieceService(db)
    try:
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(piece_id, update_dict)
        if not result:
            raise HTTPException(status_code=404, detail="Piece not found")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error updating piece {piece_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/{piece_id}")
async def delete_piece(piece_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a spare part."""
    service = PieceService(db)
    try:
        success = await service.delete(piece_id)
        if not success:
            raise HTTPException(status_code=404, detail="Piece not found")
        return {"message": "Piece deleted successfully", "id": piece_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting piece {piece_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ---------- Operational scope: machines worth linking pieces to ----------
@router.get("/scope/machines", tags=["inventory-pieces"])
async def list_in_scope_machines(
    days: int = Query(
        90, ge=1, le=365, description="Recency window (days) for WO inclusion"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Return machines that are operationally relevant for piece linking.

    A machine is "in scope" when at least one of:
      - it appears in `planning_machines` (active planning), OR
      - it has any `ordres_travail` row created within the last `days`.

    Used by the admin link-piece-to-machine UI as the default filter — admins
    can toggle to "all machines" if they need to link to one outside scope.
    """
    from sqlalchemy import distinct, select
    from datetime import datetime, timedelta, timezone
    from models.machines import Machines
    from models.planning_machines import Planning_machines
    from models.ordres_travail import Ordres_travail

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Subquery 1: machines with active planning entries
    planned = select(distinct(Planning_machines.machine_id))

    # Subquery 2: machines with recent WO activity
    recent_wo = select(distinct(Ordres_travail.machine_id)).where(
        Ordres_travail.created_at >= cutoff
    )

    in_scope_ids = planned.union(recent_wo).subquery()

    rows = (
        await db.execute(
            select(Machines.id, Machines.nom, Machines.zone, Machines.statut)
            .where(Machines.id.in_(select(in_scope_ids)))
            .order_by(Machines.nom)
        )
    ).all()

    return {
        "items": [
            {"id": r.id, "nom": r.nom, "zone": r.zone, "statut": r.statut} for r in rows
        ],
        "scope_days": days,
        "total": len(rows),
    }


# ---------- Machine Linking ----------
@router.get("/{piece_id}/machines")
async def get_piece_machines(piece_id: int, db: AsyncSession = Depends(get_db)):
    """Get machines linked to a spare part."""
    service = PieceService(db)
    try:
        machine_ids = await service.get_linked_machines(piece_id)
        return {"piece_id": piece_id, "machine_ids": machine_ids}
    except Exception as e:
        logger.exception(
            f"Error fetching machines for piece {piece_id}: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/{piece_id}/machines")
async def link_piece_to_machine(
    piece_id: int, data: LinkMachineRequest, db: AsyncSession = Depends(get_db)
):
    """Link a spare part to a machine."""
    service = PieceService(db)
    try:
        await service.link_machine(piece_id, data.machine_id)
        return {"message": f"Piece {piece_id} linked to machine {data.machine_id}"}
    except Exception as e:
        safe_err = str(e).replace("\r", "").replace("\n", "")
        logger.exception(
            f"Error linking piece {piece_id} to machine {data.machine_id}: {safe_err}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/{piece_id}/machines/{machine_id}")
async def unlink_piece_from_machine(
    piece_id: int, machine_id: int, db: AsyncSession = Depends(get_db)
):
    """Unlink a spare part from a machine."""
    service = PieceService(db)
    try:
        success = await service.unlink_machine(piece_id, machine_id)
        if not success:
            raise HTTPException(status_code=404, detail="Link not found")
        return {"message": f"Piece {piece_id} unlinked from machine {machine_id}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error unlinking piece {piece_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ---------- Smart-suggest + by-machine (for PiecePicker UI) ----------


@router.get("/suggest/lookup", tags=["inventory-pieces"])
async def suggest_pieces(
    q: str = Query(..., min_length=1, max_length=200, description="Search text"),
    machine_id: Optional[int] = Query(
        None, description="Boost pieces compatible with this machine"
    ),
    threshold_low: float = Query(0.40, ge=0.0, le=1.0),
    threshold_high: float = Query(0.80, ge=0.0, le=1.0),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Fuzzy match a free-text query against the catalog (pg_trgm similarity).

    Returns tier-classified suggestions for the pending-piece review UI and
    the technician's PiecePicker.
    """
    service = PieceService(db)
    try:
        results = await service.suggest_matches(
            query_text=q,
            machine_id=machine_id,
            threshold_low=threshold_low,
            threshold_high=threshold_high,
            limit=limit,
        )
        return {"query": q, "results": results}
    except Exception as e:
        logger.exception(f"suggest_pieces failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/by-machine/{machine_id}", tags=["inventory-pieces"])
async def list_pieces_by_machine(
    machine_id: int,
    include_consumables: bool = Query(True),
    search: Optional[str] = Query(None, max_length=200),
    db: AsyncSession = Depends(get_db),
):
    """Return pieces organized into picker-friendly sections for a machine.

    - ``compatible``  pieces linked via piece_machine
    - ``consumables`` (when ``include_consumables=true``)
    - ``other``       full-catalog matches when ``search`` provided
    """
    service = PieceService(db)
    try:
        return await service.get_pieces_by_machine(
            machine_id=machine_id,
            include_consumables=include_consumables,
            include_all_search=search,
        )
    except Exception as e:
        logger.exception(
            f"list_pieces_by_machine failed for machine {machine_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")
