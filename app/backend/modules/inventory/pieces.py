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

        result = await service.get_list(skip=skip, limit=limit, query_dict=query_dict, sort=sort)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing pieces: {str(e)}", exc_info=True)
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
        logger.error(f"Error fetching piece {piece_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=PieceResponse, status_code=201)
async def create_piece(data: PieceCreate, db: AsyncSession = Depends(get_db)):
    """Create a new spare part."""
    service = PieceService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create piece")
        logger.info(f"Piece created with id: {result.id}")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating piece: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.put("/{piece_id}", response_model=PieceResponse)
async def update_piece(piece_id: int, data: PieceUpdate, db: AsyncSession = Depends(get_db)):
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
        logger.error(f"Error updating piece {piece_id}: {str(e)}", exc_info=True)
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
        logger.error(f"Error deleting piece {piece_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ---------- Machine Linking ----------
@router.get("/{piece_id}/machines")
async def get_piece_machines(piece_id: int, db: AsyncSession = Depends(get_db)):
    """Get machines linked to a spare part."""
    service = PieceService(db)
    try:
        machine_ids = await service.get_linked_machines(piece_id)
        return {"piece_id": piece_id, "machine_ids": machine_ids}
    except Exception as e:
        logger.error(f"Error fetching machines for piece {piece_id}: {str(e)}", exc_info=True)
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
        logger.error(f"Error linking piece {piece_id} to machine {data.machine_id}: {str(e)}", exc_info=True)
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
        logger.error(f"Error unlinking piece {piece_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
