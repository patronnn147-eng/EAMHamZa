import json
import logging
from typing import List, Optional, Annotated

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.planning_utilisateurs import Planning_utilisateursService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/entities/planning_utilisateurs", tags=["planning_utilisateurs"]
)

_NOT_FOUND_MSG = "Planning_utilisateurs not found"


# ---------- Pydantic Schemas ----------
class Planning_utilisateursData(BaseModel):
    """Entity data schema (for create/update)"""

    planning_id: int
    utilisateur_id: int
    created_at: Optional[datetime] = None


class Planning_utilisateursUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""

    planning_id: Optional[int] = None
    utilisateur_id: Optional[int] = None
    created_at: Optional[datetime] = None


class Planning_utilisateursResponse(BaseModel):
    """Entity response schema"""

    id: int
    planning_id: int
    utilisateur_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Planning_utilisateursListResponse(BaseModel):
    """List response schema"""

    items: List[Planning_utilisateursResponse]
    total: int
    skip: int
    limit: int


class Planning_utilisateursBatchCreateRequest(BaseModel):
    """Batch create request"""

    items: List[Planning_utilisateursData]


class Planning_utilisateursBatchUpdateItem(BaseModel):
    """Batch update item"""

    id: int
    updates: Planning_utilisateursUpdateData


class Planning_utilisateursBatchUpdateRequest(BaseModel):
    """Batch update request"""

    items: List[Planning_utilisateursBatchUpdateItem]


class Planning_utilisateursBatchDeleteRequest(BaseModel):
    """Batch delete request"""

    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Planning_utilisateursListResponse, responses={400: {"description": "Invalid query JSON format"}, 500: {"description": "Internal Server Error"}})
async def query_planning_utilisateurss(
    *, query: Annotated[str, Query(description="Query conditions (JSON string)")] = None,
    sort: Annotated[str, Query(description="Sort field (prefix with '-' for descending)")] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(
        ge=1, le=2000, description="Max number of records to return"
    )] = 20,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Query planning_utilisateurss with filtering, sorting, and pagination"""
    logger.debug(
        f"Querying planning_utilisateurss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}"
    )

    service = Planning_utilisateursService(db)
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
        logger.debug(f"Found {result['total']} planning_utilisateurss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error querying planning_utilisateurss: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Planning_utilisateursListResponse, responses={400: {"description": "Invalid query JSON format"}, 500: {"description": "Internal Server Error"}})
async def query_planning_utilisateurss_all(
    *, query: Annotated[str, Query(description="Query conditions (JSON string)")] = None,
    sort: Annotated[str, Query(description="Sort field (prefix with '-' for descending)")] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(
        ge=1, le=2000, description="Max number of records to return"
    )] = 20,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Query planning_utilisateurss with filtering, sorting, and pagination without user limitation
    logger.debug(
        f"Querying planning_utilisateurss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}"
    )

    service = Planning_utilisateursService(db)
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
        logger.debug(f"Found {result['total']} planning_utilisateurss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error querying planning_utilisateurss: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Planning_utilisateursResponse, responses={404: {"description": "Planning_utilisateurs not found"}, 500: {"description": "Internal Server Error"}})
async def get_planning_utilisateurs(
    *, id: int,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a single planning_utilisateurs by ID"""
    logger.debug(f"Fetching planning_utilisateurs with id: {id}, fields={fields}")

    service = Planning_utilisateursService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Planning_utilisateurs with id {id} not found")
            raise HTTPException(
                status_code=404, detail=_NOT_FOUND_MSG
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error fetching planning_utilisateurs {id}: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Planning_utilisateursResponse, status_code=201, responses={400: {"description": "Failed to create planning_utilisateurs"}, 500: {"description": "Internal Server Error"}})
async def create_planning_utilisateurs(
    data: Planning_utilisateursData,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new planning_utilisateurs"""
    logger.debug(f"Creating new planning_utilisateurs with data: {data}")

    service = Planning_utilisateursService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(
                status_code=400, detail="Failed to create planning_utilisateurs"
            )

        safe_id = str(result.id).replace("\r", "").replace("\n", "")
        logger.info(f"Planning_utilisateurs created successfully with id: {safe_id}")
        return result
    except ValueError as e:
        logger.exception(f"Validation error creating planning_utilisateurs: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(
            f"Error creating planning_utilisateurs: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/batch", response_model=List[Planning_utilisateursResponse], status_code=201, 
responses={500: {"description": "Internal Server Error"}})
async def create_planning_utilisateurss_batch(
    request: Planning_utilisateursBatchCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create multiple planning_utilisateurss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} planning_utilisateurss")

    service = Planning_utilisateursService(db)
    results = []

    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)

        logger.info(f"Batch created {len(results)} planning_utilisateurss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Planning_utilisateursResponse], responses={500: {"description": "Internal Server Error"}})
async def update_planning_utilisateurss_batch(
    request: Planning_utilisateursBatchUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update multiple planning_utilisateurss in a single request"""
    logger.debug(f"Batch updating {len(request.items)} planning_utilisateurss")

    service = Planning_utilisateursService(db)
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

        logger.info(f"Batch updated {len(results)} planning_utilisateurss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Planning_utilisateursResponse, responses={400: {"description": "Bad Request"}, 404: {"description": "Planning_utilisateurs not found"}, 500: {"description": "Internal Server Error"}})
async def update_planning_utilisateurs(
    id: int,
    data: Planning_utilisateursUpdateData,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update an existing planning_utilisateurs"""
    logger.debug(f"Updating planning_utilisateurs {id} with data: {data}")

    service = Planning_utilisateursService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Planning_utilisateurs with id {id} not found for update")
            raise HTTPException(
                status_code=404, detail=_NOT_FOUND_MSG
            )

        logger.info(f"Planning_utilisateurs {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.exception(
            f"Validation error updating planning_utilisateurs {id}: {str(e)}"
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(
            f"Error updating planning_utilisateurs {id}: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch", responses={500: {"description": "Internal Server Error"}})
async def delete_planning_utilisateurss_batch(
    request: Planning_utilisateursBatchDeleteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete multiple planning_utilisateurss by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} planning_utilisateurss")

    service = Planning_utilisateursService(db)
    deleted_count = 0

    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1

        logger.info(
            f"Batch deleted {deleted_count} planning_utilisateurss successfully"
        )
        return {
            "message": f"Successfully deleted {deleted_count} planning_utilisateurss",
            "deleted_count": deleted_count,
        }
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}", responses={404: {"description": "Planning_utilisateurs not found"}, 500: {"description": "Internal Server Error"}})
async def delete_planning_utilisateurs(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a single planning_utilisateurs by ID"""
    logger.debug(f"Deleting planning_utilisateurs with id: {id}")

    service = Planning_utilisateursService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Planning_utilisateurs with id {id} not found for deletion")
            raise HTTPException(
                status_code=404, detail=_NOT_FOUND_MSG
            )

        logger.info(f"Planning_utilisateurs {id} deleted successfully")
        return {"message": "Planning_utilisateurs deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error deleting planning_utilisateurs {id}: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
