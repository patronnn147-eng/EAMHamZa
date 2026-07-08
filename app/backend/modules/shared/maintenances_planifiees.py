import json
import logging
from typing import List, Optional, Annotated

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.maintenances_planifiees import Maintenances_planifieesService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/entities/maintenances_planifiees", tags=["maintenances_planifiees"]
)

_NOT_FOUND_MSG = "Maintenances_planifiees not found"


# ---------- Pydantic Schemas ----------
class Maintenances_planifieesData(BaseModel):
    """Entity data schema (for create/update)"""

    utilisateur_id: Optional[int] = None
    rapport_id: Optional[int] = None
    date_planifiee: datetime
    description: Optional[str] = None
    created_at: Optional[datetime] = None


class Maintenances_planifieesUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""

    utilisateur_id: Optional[int] = None
    rapport_id: Optional[int] = None
    date_planifiee: Optional[datetime] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None


class Maintenances_planifieesResponse(BaseModel):
    """Entity response schema"""

    id: int
    utilisateur_id: Optional[int] = None
    rapport_id: Optional[int] = None
    date_planifiee: datetime
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Maintenances_planifieesListResponse(BaseModel):
    """List response schema"""

    items: List[Maintenances_planifieesResponse]
    total: int
    skip: int
    limit: int


class Maintenances_planifieesBatchCreateRequest(BaseModel):
    """Batch create request"""

    items: List[Maintenances_planifieesData]


class Maintenances_planifieesBatchUpdateItem(BaseModel):
    """Batch update item"""

    id: int
    updates: Maintenances_planifieesUpdateData


class Maintenances_planifieesBatchUpdateRequest(BaseModel):
    """Batch update request"""

    items: List[Maintenances_planifieesBatchUpdateItem]


class Maintenances_planifieesBatchDeleteRequest(BaseModel):
    """Batch delete request"""

    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Maintenances_planifieesListResponse, responses={400: {"description": "Invalid query JSON format"}, 500: {"description": "Internal Server Error"}})
async def query_maintenances_planifieess(
    *, query: Annotated[str, Query(description="Query conditions (JSON string)")] = None,
    sort: Annotated[str, Query(description="Sort field (prefix with '-' for descending)")] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(
        ge=1, le=2000, description="Max number of records to return"
    )] = 20,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Query maintenances_planifieess with filtering, sorting, and pagination"""
    logger.debug(
        f"Querying maintenances_planifieess: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}"
    )

    service = Maintenances_planifieesService(db)
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
        logger.debug(f"Found {result['total']} maintenances_planifieess")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error querying maintenances_planifieess: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Maintenances_planifieesListResponse, responses={400: {"description": "Invalid query JSON format"}, 500: {"description": "Internal Server Error"}})
async def query_maintenances_planifieess_all(
    *, query: Annotated[str, Query(description="Query conditions (JSON string)")] = None,
    sort: Annotated[str, Query(description="Sort field (prefix with '-' for descending)")] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(
        ge=1, le=2000, description="Max number of records to return"
    )] = 20,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Query maintenances_planifieess with filtering, sorting, and pagination without user limitation
    logger.debug(
        f"Querying maintenances_planifieess: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}"
    )

    service = Maintenances_planifieesService(db)
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
        logger.debug(f"Found {result['total']} maintenances_planifieess")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error querying maintenances_planifieess: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Maintenances_planifieesResponse, responses={404: {"description": "Maintenances_planifiees not found"}, 500: {"description": "Internal Server Error"}})
async def get_maintenances_planifiees(
    *, id: int,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a single maintenances_planifiees by ID"""
    logger.debug(f"Fetching maintenances_planifiees with id: {id}, fields={fields}")

    service = Maintenances_planifieesService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Maintenances_planifiees with id {id} not found")
            raise HTTPException(
                status_code=404, detail=_NOT_FOUND_MSG
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error fetching maintenances_planifiees {id}: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Maintenances_planifieesResponse, status_code=201, responses={400: {"description": "Failed to create maintenances_planifiees"}, 500: {"description": "Internal Server Error"}})
async def create_maintenances_planifiees(
    data: Maintenances_planifieesData,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new maintenances_planifiees"""
    logger.debug(f"Creating new maintenances_planifiees with data: {data}")

    service = Maintenances_planifieesService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(
                status_code=400, detail="Failed to create maintenances_planifiees"
            )

        safe_id = str(result.id).replace("\r", "").replace("\n", "")
        logger.info(f"Maintenances_planifiees created successfully with id: {safe_id}")
        return result
    except ValueError as e:
        logger.exception(f"Validation error creating maintenances_planifiees: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(
            f"Error creating maintenances_planifiees: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/batch", response_model=List[Maintenances_planifieesResponse], status_code=201, 
responses={500: {"description": "Internal Server Error"}})
async def create_maintenances_planifieess_batch(
    request: Maintenances_planifieesBatchCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create multiple maintenances_planifieess in a single request"""
    logger.debug(f"Batch creating {len(request.items)} maintenances_planifieess")

    service = Maintenances_planifieesService(db)
    results = []

    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)

        logger.info(
            f"Batch created {len(results)} maintenances_planifieess successfully"
        )
        return results
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Maintenances_planifieesResponse], responses={500: {"description": "Internal Server Error"}})
async def update_maintenances_planifieess_batch(
    request: Maintenances_planifieesBatchUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update multiple maintenances_planifieess in a single request"""
    logger.debug(f"Batch updating {len(request.items)} maintenances_planifieess")

    service = Maintenances_planifieesService(db)
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
            f"Batch updated {len(results)} maintenances_planifieess successfully"
        )
        return results
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Maintenances_planifieesResponse, responses={400: {"description": "Bad Request"}, 404: {"description": "Maintenances_planifiees not found"}, 500: {"description": "Internal Server Error"}})
async def update_maintenances_planifiees(
    id: int,
    data: Maintenances_planifieesUpdateData,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update an existing maintenances_planifiees"""
    logger.debug(f"Updating maintenances_planifiees {id} with data: {data}")

    service = Maintenances_planifieesService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Maintenances_planifiees with id {id} not found for update")
            raise HTTPException(
                status_code=404, detail=_NOT_FOUND_MSG
            )

        logger.info(f"Maintenances_planifiees {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.exception(
            f"Validation error updating maintenances_planifiees {id}: {str(e)}"
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(
            f"Error updating maintenances_planifiees {id}: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch", responses={500: {"description": "Internal Server Error"}})
async def delete_maintenances_planifieess_batch(
    request: Maintenances_planifieesBatchDeleteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete multiple maintenances_planifieess by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} maintenances_planifieess")

    service = Maintenances_planifieesService(db)
    deleted_count = 0

    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1

        logger.info(
            f"Batch deleted {deleted_count} maintenances_planifieess successfully"
        )
        return {
            "message": f"Successfully deleted {deleted_count} maintenances_planifieess",
            "deleted_count": deleted_count,
        }
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}", responses={404: {"description": "Maintenances_planifiees not found"}, 500: {"description": "Internal Server Error"}})
async def delete_maintenances_planifiees(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a single maintenances_planifiees by ID"""
    logger.debug(f"Deleting maintenances_planifiees with id: {id}")

    service = Maintenances_planifieesService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(
                f"Maintenances_planifiees with id {id} not found for deletion"
            )
            raise HTTPException(
                status_code=404, detail=_NOT_FOUND_MSG
            )

        logger.info(f"Maintenances_planifiees {id} deleted successfully")
        return {"message": "Maintenances_planifiees deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error deleting maintenances_planifiees {id}: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
