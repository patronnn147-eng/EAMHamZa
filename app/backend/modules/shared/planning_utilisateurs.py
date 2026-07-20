import json
import logging
from typing import List, Optional, Annotated

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.planning_utilisateurs import PlanningUtilisateursService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/entities/PlanningUtilisateurs", tags=["PlanningUtilisateurs"]
)

_NOT_FOUND_MSG = "PlanningUtilisateurs not found"


# ---------- Pydantic Schemas ----------
class PlanningUtilisateursData(BaseModel):
    """Entity data schema (for create/update)"""

    planning_id: int
    utilisateur_id: int
    created_at: Optional[datetime] = None


class PlanningUtilisateursUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""

    planning_id: Optional[int] = None
    utilisateur_id: Optional[int] = None
    created_at: Optional[datetime] = None


class PlanningUtilisateursResponse(BaseModel):
    """Entity response schema"""

    id: int
    planning_id: int
    utilisateur_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PlanningUtilisateursListResponse(BaseModel):
    """List response schema"""

    items: List[PlanningUtilisateursResponse]
    total: int
    skip: int
    limit: int


class PlanningUtilisateursBatchCreateRequest(BaseModel):
    """Batch create request"""

    items: List[PlanningUtilisateursData]


class PlanningUtilisateursBatchUpdateItem(BaseModel):
    """Batch update item"""

    id: int
    updates: PlanningUtilisateursUpdateData


class PlanningUtilisateursBatchUpdateRequest(BaseModel):
    """Batch update request"""

    items: List[PlanningUtilisateursBatchUpdateItem]


class PlanningUtilisateursBatchDeleteRequest(BaseModel):
    """Batch delete request"""

    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=PlanningUtilisateursListResponse, responses={400: {"description": "Invalid query JSON format"}, 500: {"description": "Internal Server Error"}})
async def query_PlanningUtilisateurss(
    *, query: Annotated[str, Query(description="Query conditions (JSON string)")] = None,
    sort: Annotated[str, Query(description="Sort field (prefix with '-' for descending)")] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(
        ge=1, le=2000, description="Max number of records to return"
    )] = 20,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Query PlanningUtilisateurss with filtering, sorting, and pagination"""
    logger.debug(
        f"Querying PlanningUtilisateurss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}"
    )

    service = PlanningUtilisateursService(db)
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
        logger.debug(f"Found {result['total']} PlanningUtilisateurss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error querying PlanningUtilisateurss: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=PlanningUtilisateursListResponse, responses={400: {"description": "Invalid query JSON format"}, 500: {"description": "Internal Server Error"}})
async def query_PlanningUtilisateurss_all(
    *, query: Annotated[str, Query(description="Query conditions (JSON string)")] = None,
    sort: Annotated[str, Query(description="Sort field (prefix with '-' for descending)")] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(
        ge=1, le=2000, description="Max number of records to return"
    )] = 20,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Query PlanningUtilisateurss with filtering, sorting, and pagination without user limitation
    logger.debug(
        f"Querying PlanningUtilisateurss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}"
    )

    service = PlanningUtilisateursService(db)
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
        logger.debug(f"Found {result['total']} PlanningUtilisateurss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error querying PlanningUtilisateurss: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=PlanningUtilisateursResponse, responses={404: {"description": "PlanningUtilisateurs not found"}, 500: {"description": "Internal Server Error"}})
async def get_PlanningUtilisateurs(
    *, id: int,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a single PlanningUtilisateurs by ID"""
    logger.debug(f"Fetching PlanningUtilisateurs with id: {id}, fields={fields}")

    service = PlanningUtilisateursService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"PlanningUtilisateurs with id {id} not found")
            raise HTTPException(
                status_code=404, detail=_NOT_FOUND_MSG
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error fetching PlanningUtilisateurs {id}: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=PlanningUtilisateursResponse, status_code=201, responses={400: {"description": "Failed to create PlanningUtilisateurs"}, 500: {"description": "Internal Server Error"}})
async def create_PlanningUtilisateurs(
    data: PlanningUtilisateursData,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new PlanningUtilisateurs"""
    logger.debug(f"Creating new PlanningUtilisateurs with data: {data}")

    service = PlanningUtilisateursService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(
                status_code=400, detail="Failed to create PlanningUtilisateurs"
            )

        safe_id = str(result.id).replace("\r", "").replace("\n", "")
        logger.info(f"PlanningUtilisateurs created successfully with id: {safe_id}")
        return result
    except ValueError as e:
        logger.exception(f"Validation error creating PlanningUtilisateurs: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(
            f"Error creating PlanningUtilisateurs: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/batch", response_model=List[PlanningUtilisateursResponse], status_code=201, 
responses={500: {"description": "Internal Server Error"}})
async def create_PlanningUtilisateurss_batch(
    request: PlanningUtilisateursBatchCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create multiple PlanningUtilisateurss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} PlanningUtilisateurss")

    service = PlanningUtilisateursService(db)
    results = []

    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)

        logger.info(f"Batch created {len(results)} PlanningUtilisateurss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[PlanningUtilisateursResponse], responses={500: {"description": "Internal Server Error"}})
async def update_PlanningUtilisateurss_batch(
    request: PlanningUtilisateursBatchUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update multiple PlanningUtilisateurss in a single request"""
    logger.debug(f"Batch updating {len(request.items)} PlanningUtilisateurss")

    service = PlanningUtilisateursService(db)
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

        logger.info(f"Batch updated {len(results)} PlanningUtilisateurss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=PlanningUtilisateursResponse, responses={400: {"description": "Bad Request"}, 404: {"description": "PlanningUtilisateurs not found"}, 500: {"description": "Internal Server Error"}})
async def update_PlanningUtilisateurs(
    id: int,
    data: PlanningUtilisateursUpdateData,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update an existing PlanningUtilisateurs"""
    logger.debug(f"Updating PlanningUtilisateurs {id} with data: {data}")

    service = PlanningUtilisateursService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"PlanningUtilisateurs with id {id} not found for update")
            raise HTTPException(
                status_code=404, detail=_NOT_FOUND_MSG
            )

        logger.info(f"PlanningUtilisateurs {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.exception(
            f"Validation error updating PlanningUtilisateurs {id}: {str(e)}"
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(
            f"Error updating PlanningUtilisateurs {id}: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch", responses={500: {"description": "Internal Server Error"}})
async def delete_PlanningUtilisateurss_batch(
    request: PlanningUtilisateursBatchDeleteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete multiple PlanningUtilisateurss by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} PlanningUtilisateurss")

    service = PlanningUtilisateursService(db)
    deleted_count = 0

    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1

        logger.info(
            f"Batch deleted {deleted_count} PlanningUtilisateurss successfully"
        )
        return {
            "message": f"Successfully deleted {deleted_count} PlanningUtilisateurss",
            "deleted_count": deleted_count,
        }
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}", responses={404: {"description": "PlanningUtilisateurs not found"}, 500: {"description": "Internal Server Error"}})
async def delete_PlanningUtilisateurs(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a single PlanningUtilisateurs by ID"""
    logger.debug(f"Deleting PlanningUtilisateurs with id: {id}")

    service = PlanningUtilisateursService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"PlanningUtilisateurs with id {id} not found for deletion")
            raise HTTPException(
                status_code=404, detail=_NOT_FOUND_MSG
            )

        logger.info(f"PlanningUtilisateurs {id} deleted successfully")
        return {"message": "PlanningUtilisateurs deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error deleting PlanningUtilisateurs {id}: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
