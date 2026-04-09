import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.pagination import PaginatedResponse

from core.database import get_db
from services.inventory import StockService
from schemas.stock import (
    StockResponse,
    StockAddRequest,
    StockConsumeRequest,
    MouvementStockResponse,
    AlerteStockResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/inventory/stock", tags=["inventory-stock"])


# ---------- Stock Levels ----------
@router.get("", response_model=PaginatedResponse[StockResponse])
async def list_stock_levels(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get current stock levels for all parts with pagination."""
    service = StockService(db)
    try:
        skip = (page - 1) * size
        result = await service.get_stock_levels(skip=skip, limit=size)
        return PaginatedResponse.create(
            items=result["items"],
            total=result["total"],
            page=page,
            size=size
        )
    except Exception as e:
        logger.error(f"Error listing stock levels: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ---------- Add Stock ----------
@router.post("", response_model=StockResponse, status_code=201)
async def add_stock(data: StockAddRequest, db: AsyncSession = Depends(get_db)):
    """Add stock for a spare part (e.g., received delivery)."""
    service = StockService(db)
    try:
        result = await service.add_stock(
            piece_id=data.piece_id,
            quantity=data.quantity,
            reference=data.reference,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding stock: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ---------- Consume Stock ----------
@router.post("/consume", response_model=StockResponse)
async def consume_stock(data: StockConsumeRequest, db: AsyncSession = Depends(get_db)):
    """Consume stock for a spare part (e.g., used in an intervention)."""
    service = StockService(db)
    try:
        result = await service.consume_stock(
            piece_id=data.piece_id,
            quantity=data.quantity,
            intervention_id=data.intervention_id,
            reference=data.reference,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error consuming stock: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ---------- Low Stock Alerts ----------
@router.get("/alertes", response_model=PaginatedResponse[AlerteStockResponse])
async def get_stock_alerts(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get alerts for parts with stock below minimum threshold with pagination."""
    service = StockService(db)
    try:
        skip = (page - 1) * size
        result = await service.get_alerts(skip=skip, limit=size)
        return PaginatedResponse.create(
            items=result["items"],
            total=result["total"],
            page=page,
            size=size
        )
    except Exception as e:
        logger.error(f"Error fetching stock alerts: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ---------- Stock Movements History ----------
@router.get("/movements", response_model=PaginatedResponse[MouvementStockResponse])
async def get_stock_movements(
    piece_id: Optional[int] = Query(None, description="Filter by piece ID"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Get stock movement history (additions and consumptions) with pagination."""
    service = StockService(db)
    try:
        skip = (page - 1) * size
        result = await service.get_movements(piece_id=piece_id, skip=skip, limit=size)
        return PaginatedResponse.create(
            items=result["items"],
            total=result["total"],
            page=page,
            size=size
        )
    except Exception as e:
        logger.error(f"Error fetching stock movements: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
