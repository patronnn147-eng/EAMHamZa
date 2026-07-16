import json
import logging
from typing import List, Optional, Annotated

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.MaintenancesPlanifiees import MaintenancesPlanifieesService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/entities/MaintenancesPlanifiees", tags=["MaintenancesPlanifiees"]
)

_NOT_FOUND_MSG = "MaintenancesPlanifiees not found"


# ---------- Pydantic Schemas ----------
class MaintenancesPlanifieesData(BaseModel):
    """Entity data schema (for create/update)"""

    utilisateur_id: Optional[int] = None
    rapport_id: Optional[int] = None
    date_planifiee: datetime
    description: Optional[str] = None
    created_at: Optional[datetime] = None


class MaintenancesPlanifieesUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""

    utilisateur_id: Optional[int] = None
    rapport_id: Optional[int] = None
    date_planifiee: Optional[datetime] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None


class MaintenancesPlanifieesResponse(BaseModel):
    """Entity response schema"""

    id: int
    utilisateur_id: Optional[int] = None
    rapport_id: Optional[int] = None
    date_planifiee: datetime
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MaintenancesPlanifieesListResponse(BaseModel):
    """List response schema"""

    items: List[MaintenancesPlanifieesResponse]
    total: int
    skip: int
    limit: int


class MaintenancesPlanifieesBatchCreateRequest(BaseModel):
    """Batch create request"""

    items: List[MaintenancesPlanifieesData]


class MaintenancesPlanifieesBatchUpdateItem(BaseModel):
    """Batch update item"""

    id: int
    updates: MaintenancesPlanifieesUpdateData


class MaintenancesPlanifieesBatchUpdateRequest(BaseModel):
    """Batch update request"""

    items: List[MaintenancesPlanifieesBatchUpdateItem]


class MaintenancesPlanifieesBatchDeleteRequest(BaseModel):
    """Batch delete request"""

    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=MaintenancesPlanifieesListResponse, responses={400: {"description": "Invalid query JSON format"}, 500: {"description": "Internal Server Error"}})
async def query_MaintenancesPlanifieess(
    *, query: Annotated[str, Query(description="Query conditions (JSON string)")] = None,
    sort: Annotated[str, Query(description="Sort field (prefix with '-' for descending)")] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(
        ge=1, le=2000, description="Max number of records to return"
    )] = 20,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Query MaintenancesPlanifieess with filtering, sorting, and pagination"""
    logger.debug(
        f"Querying MaintenancesPlanifieess: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}"
    )

    service = MaintenancesPlanifieesService(db)
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
        logger.debug(f"Found {result['total']} MaintenancesPlanifieess")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error querying MaintenancesPlanifieess: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=MaintenancesPlanifieesListResponse, responses={400: {"description": "Invalid query JSON format"}, 500: {"description": "Internal Server Error"}})
async def query_MaintenancesPlanifieess_all(
    *, query: Annotated[str, Query(description="Query conditions (JSON string)")] = None,
    sort: Annotated[str, Query(description="Sort field (prefix with '-' for descending)")] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(
        ge=1, le=2000, description="Max number of records to return"
    )] = 20,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Query MaintenancesPlanifieess with filtering, sorting, and pagination without user limitation
    logger.debug(
        f"Querying MaintenancesPlanifieess: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}"
    )

    service = MaintenancesPlanifieesService(db)
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
        logger.debug(f"Found {result['total']} MaintenancesPlanifieess")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error querying MaintenancesPlanifieess: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=MaintenancesPlanifieesResponse, responses={404: {"description": "MaintenancesPlanifiees not found"}, 500: {"description": "Internal Server Error"}})
async def get_MaintenancesPlanifiees(
    *, id: int,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a single MaintenancesPlanifiees by ID"""
    logger.debug(f"Fetching MaintenancesPlanifiees with id: {id}, fields={fields}")

    service = MaintenancesPlanifieesService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"MaintenancesPlanifiees with id {id} not found")
            raise HTTPException(
                status_code=404, detail=_NOT_FOUND_MSG
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error fetching MaintenancesPlanifiees {id}: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=MaintenancesPlanifieesResponse, status_code=201, responses={400: {"description": "Failed to create MaintenancesPlanifiees"}, 500: {"description": "Internal Server Error"}})
async def create_MaintenancesPlanifiees(
    data: MaintenancesPlanifieesData,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new MaintenancesPlanifiees"""
    logger.debug(f"Creating new MaintenancesPlanifiees with data: {data}")

    service = MaintenancesPlanifieesService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(
                status_code=400, detail="Failed to create MaintenancesPlanifiees"
            )

        safe_id = str(result.id).replace("\r", "").replace("\n", "")
        logger.info(f"MaintenancesPlanifiees created successfully with id: {safe_id}")
        return result
    except ValueError as e:
        logger.exception(f"Validation error creating MaintenancesPlanifiees: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(
            f"Error creating MaintenancesPlanifiees: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/batch", response_model=List[MaintenancesPlanifieesResponse], status_code=201, 
responses={500: {"description": "Internal Server Error"}})
async def create_MaintenancesPlanifieess_batch(
    request: MaintenancesPlanifieesBatchCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create multiple MaintenancesPlanifieess in a single request"""
    logger.debug(f"Batch creating {len(request.items)} MaintenancesPlanifieess")

    service = MaintenancesPlanifieesService(db)
    results = []

    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)

        logger.info(
            f"Batch created {len(results)} MaintenancesPlanifieess successfully"
        )
        return results
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[MaintenancesPlanifieesResponse], responses={500: {"description": "Internal Server Error"}})
async def update_MaintenancesPlanifieess_batch(
    request: MaintenancesPlanifieesBatchUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update multiple MaintenancesPlanifieess in a single request"""
    logger.debug(f"Batch updating {len(request.items)} MaintenancesPlanifieess")

    service = MaintenancesPlanifieesService(db)
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

        logger.info(
            f"Batch updated {len(results)} MaintenancesPlanifieess successfully"
        )
        return results
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=MaintenancesPlanifieesResponse, responses={400: {"description": "Bad Request"}, 404: {"description": "MaintenancesPlanifiees not found"}, 500: {"description": "Internal Server Error"}})
async def update_MaintenancesPlanifiees(
    id: int,
    data: MaintenancesPlanifieesUpdateData,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update an existing MaintenancesPlanifiees"""
    logger.debug(f"Updating MaintenancesPlanifiees {id} with data: {data}")

    service = MaintenancesPlanifieesService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"MaintenancesPlanifiees with id {id} not found for update")
            raise HTTPException(
                status_code=404, detail=_NOT_FOUND_MSG
            )

        logger.info(f"MaintenancesPlanifiees {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.exception(
            f"Validation error updating MaintenancesPlanifiees {id}: {str(e)}"
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(
            f"Error updating MaintenancesPlanifiees {id}: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch", responses={500: {"description": "Internal Server Error"}})
async def delete_MaintenancesPlanifieess_batch(
    request: MaintenancesPlanifieesBatchDeleteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete multiple MaintenancesPlanifieess by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} MaintenancesPlanifieess")

    service = MaintenancesPlanifieesService(db)
    deleted_count = 0

    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1

        logger.info(
            f"Batch deleted {deleted_count} MaintenancesPlanifieess successfully"
        )
        return {
            "message": f"Successfully deleted {deleted_count} MaintenancesPlanifieess",
            "deleted_count": deleted_count,
        }
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}", responses={404: {"description": "MaintenancesPlanifiees not found"}, 500: {"description": "Internal Server Error"}})
async def delete_MaintenancesPlanifiees(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a single MaintenancesPlanifiees by ID"""
    logger.debug(f"Deleting MaintenancesPlanifiees with id: {id}")

    service = MaintenancesPlanifieesService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(
                f"MaintenancesPlanifiees with id {id} not found for deletion"
            )
            raise HTTPException(
                status_code=404, detail=_NOT_FOUND_MSG
            )

        logger.info(f"MaintenancesPlanifiees {id} deleted successfully")
        return {"message": "MaintenancesPlanifiees deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error deleting MaintenancesPlanifiees {id}: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
