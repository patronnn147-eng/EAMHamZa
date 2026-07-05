import json
import logging
from typing import List, Optional

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.rapports import RapportsService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/rapports", tags=["rapports"])


# ---------- Pydantic Schemas ----------
class RapportsData(BaseModel):
    """Entity data schema (for create/update)"""

    identifiant_rapport: str
    titre: str
    date_generation: datetime
    contenu: str
    utilisateur_id: int = None
    created_at: Optional[datetime] = None


class RapportsUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""

    identifiant_rapport: Optional[str] = None
    titre: Optional[str] = None
    date_generation: Optional[datetime] = None
    contenu: Optional[str] = None
    utilisateur_id: Optional[int] = None
    created_at: Optional[datetime] = None


class RapportsResponse(BaseModel):
    """Entity response schema"""

    id: int
    identifiant_rapport: str
    titre: str
    date_generation: datetime
    contenu: str
    utilisateur_id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RapportsListResponse(BaseModel):
    """List response schema"""

    items: List[RapportsResponse]
    total: int
    skip: int
    limit: int


class RapportsBatchCreateRequest(BaseModel):
    """Batch create request"""

    items: List[RapportsData]


class RapportsBatchUpdateItem(BaseModel):
    """Batch update item"""

    id: int
    updates: RapportsUpdateData


class RapportsBatchUpdateRequest(BaseModel):
    """Batch update request"""

    items: List[RapportsBatchUpdateItem]


class RapportsBatchDeleteRequest(BaseModel):
    """Batch delete request"""

    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=RapportsListResponse)
async def query_rapportss(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        20, ge=1, le=2000, description="Max number of records to return"
    ),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query rapportss with filtering, sorting, and pagination"""
    logger.debug(
        f"Querying rapportss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}"
    )

    service = RapportsService(db)
    try:
        # Parse query JSON if provided
        query_dict = None
        if query:
            try:
                query_dict = json.loads(query)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid query JSON format")

        result = await service.get_list(
            skip=skip,
            limit=limit,
            query_dict=query_dict,
            sort=sort,
        )
        logger.debug(f"Found {result['total']} rapportss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error querying rapportss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=RapportsListResponse)
async def query_rapportss_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        20, ge=1, le=2000, description="Max number of records to return"
    ),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query rapportss with filtering, sorting, and pagination without user limitation
    logger.debug(
        f"Querying rapportss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}"
    )

    service = RapportsService(db)
    try:
        # Parse query JSON if provided
        query_dict = None
        if query:
            try:
                query_dict = json.loads(query)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid query JSON format")

        result = await service.get_list(
            skip=skip, limit=limit, query_dict=query_dict, sort=sort
        )
        logger.debug(f"Found {result['total']} rapportss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error querying rapportss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=RapportsResponse)
async def get_rapports(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single rapports by ID"""
    logger.debug(f"Fetching rapports with id: {id}, fields={fields}")

    service = RapportsService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Rapports with id {id} not found")
            raise HTTPException(status_code=404, detail="Rapports not found")

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching rapports {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=RapportsResponse, status_code=201)
async def create_rapports(
    data: RapportsData,
    db: AsyncSession = Depends(get_db),
):
    """Create a new rapports"""
    logger.debug(f"Creating new rapports with data: {data}")

    service = RapportsService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create rapports")

        logger.info(f"Rapports created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.exception(f"Validation error creating rapports: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error creating rapports: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[RapportsResponse], status_code=201)
async def create_rapportss_batch(
    request: RapportsBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple rapportss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} rapportss")

    service = RapportsService(db)
    results = []

    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)

        logger.info(f"Batch created {len(results)} rapportss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[RapportsResponse])
async def update_rapportss_batch(
    request: RapportsBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple rapportss in a single request"""
    logger.debug(f"Batch updating {len(request.items)} rapportss")

    service = RapportsService(db)
    results = []

    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {
                k: v for k, v in item.updates.model_dump().items() if v is not None
            }
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)

        logger.info(f"Batch updated {len(results)} rapportss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=RapportsResponse)
async def update_rapports(
    id: int,
    data: RapportsUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing rapports"""
    logger.debug(f"Updating rapports {id} with data: {data}")

    service = RapportsService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Rapports with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Rapports not found")

        logger.info(f"Rapports {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.exception(f"Validation error updating rapports {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error updating rapports {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_rapportss_batch(
    request: RapportsBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple rapportss by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} rapportss")

    service = RapportsService(db)
    deleted_count = 0

    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1

        logger.info(f"Batch deleted {deleted_count} rapportss successfully")
        return {
            "message": f"Successfully deleted {deleted_count} rapportss",
            "deleted_count": deleted_count,
        }
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_rapports(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single rapports by ID"""
    logger.debug(f"Deleting rapports with id: {id}")

    service = RapportsService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Rapports with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Rapports not found")

        logger.info(f"Rapports {id} deleted successfully")
        return {"message": "Rapports deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting rapports {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
