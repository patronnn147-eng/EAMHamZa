"""Live availability endpoints — read-only observability for stock + reservations."""

import logging
from decimal import Decimal
from typing import List, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.inventory import InventoryReservationService
from schemas.stock import AvailabilityResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/inventory/availability", tags=["inventory-availability"]
)


@router.get("/{piece_id}", response_model=AvailabilityResponse)
async def get_availability(piece_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    """Return raw stock, reserved total, and computed available qty for one piece."""
    try:
        svc = InventoryReservationService(db)
        avail_map = await svc.get_availability_map([piece_id])
        info = avail_map.get(
            piece_id,
            {"stock": Decimal(0), "reserved": Decimal(0), "available": Decimal(0)},
        )
        return AvailabilityResponse(
            piece_id=piece_id,
            stock_quantity=info["stock"],
            reserved_quantity=info["reserved"],
            available_quantity=info["available"],
        )
    except Exception as e:
        logger.exception(
            f"get_availability failed for piece {piece_id}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=List[AvailabilityResponse])
async def get_availability_batch(
    piece_ids: Annotated[str, Query(description="Comma-separated piece IDs")],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Batch availability lookup — single query, returns one row per input id."""
    try:
        ids = []
        for tok in piece_ids.split(","):
            tok = tok.strip()
            if not tok:
                continue
            try:
                ids.append(int(tok))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid piece_id: {tok}")
        if len(ids) > 200:
            raise HTTPException(
                status_code=400, detail="At most 200 piece IDs per request"
            )
        if not ids:
            return []

        svc = InventoryReservationService(db)
        avail_map = await svc.get_availability_map(ids)

        return [
            AvailabilityResponse(
                piece_id=pid,
                stock_quantity=avail_map.get(pid, {}).get("stock", Decimal(0)),
                reserved_quantity=avail_map.get(pid, {}).get("reserved", Decimal(0)),
                available_quantity=avail_map.get(pid, {}).get("available", Decimal(0)),
            )
            for pid in ids
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"get_availability_batch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
