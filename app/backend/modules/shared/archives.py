import json
import logging
from typing import List, Optional, Annotated

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.archives import ArchivesService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/archives", tags=["archives"])


# ---------- Pydantic Schemas ----------
class ArchivesData(BaseModel):
    """Entity data schema (for create/update)"""

    identifiant_archive: str
    nom: str
    date_archivage: datetime
    type: str
    object_key: str = None
    ordre_travail_id: Optional[int] = None
    created_at: Optional[datetime] = None


class ArchivesUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""

    identifiant_archive: Optional[str] = None
    nom: Optional[str] = None
    date_archivage: Optional[datetime] = None
    type: Optional[str] = None
    object_key: Optional[str] = None
    ordre_travail_id: Optional[int] = None
    created_at: Optional[datetime] = None


class ArchivesResponse(BaseModel):
    """Entity response schema"""

    id: int
    identifiant_archive: str
    nom: str
    date_archivage: datetime
    type: str
    object_key: Optional[str] = None
    ordre_travail_id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ArchivesListResponse(BaseModel):
    """List response schema"""

    items: List[ArchivesResponse]
    total: int
    skip: int
    limit: int


class ArchivesBatchCreateRequest(BaseModel):
    """Batch create request"""

    items: List[ArchivesData]


class ArchivesBatchUpdateItem(BaseModel):
    """Batch update item"""

    id: int
    updates: ArchivesUpdateData


class ArchivesBatchUpdateRequest(BaseModel):
    """Batch update request"""

    items: List[ArchivesBatchUpdateItem]


class ArchivesBatchDeleteRequest(BaseModel):
    """Batch delete request"""

    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=ArchivesListResponse)
async def query_archivess(
    *, query: Annotated[str, Query(description="Query conditions (JSON string)")] = None,
    sort: Annotated[str, Query(description="Sort field (prefix with '-' for descending)")] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(
        ge=1, le=2000, description="Max number of records to return"
    )] = 20,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Query archivess with filtering, sorting, and pagination"""
    logger.debug(
        f"Querying archivess: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}"
    )

    service = ArchivesService(db)
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
        logger.debug(f"Found {result['total']} archivess")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error querying archivess: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=ArchivesListResponse)
async def query_archivess_all(
    *, query: Annotated[str, Query(description="Query conditions (JSON string)")] = None,
    sort: Annotated[str, Query(description="Sort field (prefix with '-' for descending)")] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(
        ge=1, le=2000, description="Max number of records to return"
    )] = 20,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Query archivess with filtering, sorting, and pagination without user limitation
    logger.debug(
        f"Querying archivess: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}"
    )

    service = ArchivesService(db)
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
        logger.debug(f"Found {result['total']} archivess")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error querying archivess: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=ArchivesResponse)
async def get_archives(
    *, id: int,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a single archives by ID"""
    logger.debug(f"Fetching archives with id: {id}, fields={fields}")

    service = ArchivesService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Archives with id {id} not found")
            raise HTTPException(status_code=404, detail="Archives not found")

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching archives {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=ArchivesResponse, status_code=201)
async def create_archives(
    data: ArchivesData,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new archives"""
    logger.debug(f"Creating new archives with data: {data}")

    service = ArchivesService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create archives")

        safe_id = str(result.id).replace("\r", "").replace("\n", "")
        logger.info(f"Archives created successfully with id: {safe_id}")
        return result
    except ValueError as e:
        logger.exception(f"Validation error creating archives: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error creating archives: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[ArchivesResponse], status_code=201)
async def create_archivess_batch(
    request: ArchivesBatchCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create multiple archivess in a single request"""
    logger.debug(f"Batch creating {len(request.items)} archivess")

    service = ArchivesService(db)
    results = []

    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)

        logger.info(f"Batch created {len(results)} archivess successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[ArchivesResponse])
async def update_archivess_batch(
    request: ArchivesBatchUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update multiple archivess in a single request"""
    logger.debug(f"Batch updating {len(request.items)} archivess")

    service = ArchivesService(db)
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

        logger.info(f"Batch updated {len(results)} archivess successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=ArchivesResponse)
async def update_archives(
    id: int,
    data: ArchivesUpdateData,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update an existing archives"""
    logger.debug(f"Updating archives {id} with data: {data}")

    service = ArchivesService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Archives with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Archives not found")

        logger.info(f"Archives {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.exception(f"Validation error updating archives {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error updating archives {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_archivess_batch(
    request: ArchivesBatchDeleteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete multiple archivess by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} archivess")

    service = ArchivesService(db)
    deleted_count = 0

    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1

        logger.info(f"Batch deleted {deleted_count} archivess successfully")
        return {
            "message": f"Successfully deleted {deleted_count} archivess",
            "deleted_count": deleted_count,
        }
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_archives(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a single archives by ID"""
    logger.debug(f"Deleting archives with id: {id}")

    service = ArchivesService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Archives with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Archives not found")

        logger.info(f"Archives {id} deleted successfully")
        return {"message": "Archives deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting archives {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
