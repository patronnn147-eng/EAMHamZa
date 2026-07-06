import json
import logging
from typing import List, Optional, Annotated

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.ordres import OrdresService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/ordres", tags=["ordres"])

_NOT_FOUND_MSG = "Ordres not found"


# ---------- Pydantic Schemas ----------
class OrdresData(BaseModel):
    """Entity data schema (for create/update)"""

    identifiant: str
    titre: str
    description: str = None
    date_creation: datetime
    statut: str
    created_at: Optional[datetime] = None


class OrdresUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""

    identifiant: Optional[str] = None
    titre: Optional[str] = None
    description: Optional[str] = None
    date_creation: Optional[datetime] = None
    statut: Optional[str] = None
    created_at: Optional[datetime] = None


class OrdresResponse(BaseModel):
    """Entity response schema"""

    id: int
    identifiant: str
    titre: str
    description: Optional[str] = None
    date_creation: datetime
    statut: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OrdresListResponse(BaseModel):
    """List response schema"""

    items: List[OrdresResponse]
    total: int
    skip: int
    limit: int


class OrdresBatchCreateRequest(BaseModel):
    """Batch create request"""

    items: List[OrdresData]


class OrdresBatchUpdateItem(BaseModel):
    """Batch update item"""

    id: int
    updates: OrdresUpdateData


class OrdresBatchUpdateRequest(BaseModel):
    """Batch update request"""

    items: List[OrdresBatchUpdateItem]


class OrdresBatchDeleteRequest(BaseModel):
    """Batch delete request"""

    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=OrdresListResponse, responses={400: {"description": "Invalid query JSON format"}, 500: {"description": "Internal Server Error"}})
async def query_ordress(
    *, query: Annotated[str, Query(description="Query conditions (JSON string)")] = None,
    sort: Annotated[str, Query(description="Sort field (prefix with '-' for descending)")] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(
        ge=1, le=2000, description="Max number of records to return"
    )] = 20,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Query ordress with filtering, sorting, and pagination"""
    logger.debug(
        f"Querying ordress: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}"
    )

    service = OrdresService(db)
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
        logger.debug(f"Found {result['total']} ordress")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error querying ordress: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=OrdresListResponse, responses={400: {"description": "Invalid query JSON format"}, 500: {"description": "Internal Server Error"}})
async def query_ordress_all(
    *, query: Annotated[str, Query(description="Query conditions (JSON string)")] = None,
    sort: Annotated[str, Query(description="Sort field (prefix with '-' for descending)")] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(
        ge=1, le=2000, description="Max number of records to return"
    )] = 20,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Query ordress with filtering, sorting, and pagination without user limitation
    logger.debug(
        f"Querying ordress: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}"
    )

    service = OrdresService(db)
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
        logger.debug(f"Found {result['total']} ordress")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error querying ordress: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=OrdresResponse, responses={404: {"description": "Ordres not found"}, 500: {"description": "Internal Server Error"}})
async def get_ordres(
    *, id: int,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a single ordres by ID"""
    logger.debug(f"Fetching ordres with id: {id}, fields={fields}")

    service = OrdresService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Ordres with id {id} not found")
            raise HTTPException(status_code=404, detail=_NOT_FOUND_MSG)

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching ordres {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=OrdresResponse, status_code=201, responses={400: {"description": "Failed to create ordres"}, 500: {"description": "Internal Server Error"}})
async def create_ordres(
    data: OrdresData,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new ordres"""
    logger.debug(f"Creating new ordres with data: {data}")

    service = OrdresService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create ordres")

        safe_id = str(result.id).replace("\r", "").replace("\n", "")
        logger.info(f"Ordres created successfully with id: {safe_id}")
        return result
    except ValueError as e:
        logger.exception(f"Validation error creating ordres: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error creating ordres: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[OrdresResponse], status_code=201, responses={500: {"description": "Internal Server Error"}})
async def create_ordress_batch(
    request: OrdresBatchCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create multiple ordress in a single request"""
    logger.debug(f"Batch creating {len(request.items)} ordress")

    service = OrdresService(db)
    results = []

    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)

        logger.info(f"Batch created {len(results)} ordress successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[OrdresResponse], responses={500: {"description": "Internal Server Error"}})
async def update_ordress_batch(
    request: OrdresBatchUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update multiple ordress in a single request"""
    logger.debug(f"Batch updating {len(request.items)} ordress")

    service = OrdresService(db)
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

        logger.info(f"Batch updated {len(results)} ordress successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=OrdresResponse, responses={400: {"description": "Bad Request"}, 404: {"description": "Ordres not found"}, 500: {"description": "Internal Server Error"}})
async def update_ordres(
    id: int,
    data: OrdresUpdateData,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update an existing ordres"""
    logger.debug(f"Updating ordres {id} with data: {data}")

    service = OrdresService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Ordres with id {id} not found for update")
            raise HTTPException(status_code=404, detail=_NOT_FOUND_MSG)

        logger.info(f"Ordres {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.exception(f"Validation error updating ordres {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error updating ordres {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch", responses={500: {"description": "Internal Server Error"}})
async def delete_ordress_batch(
    request: OrdresBatchDeleteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete multiple ordress by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} ordress")

    service = OrdresService(db)
    deleted_count = 0

    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1

        logger.info(f"Batch deleted {deleted_count} ordress successfully")
        return {
            "message": f"Successfully deleted {deleted_count} ordress",
            "deleted_count": deleted_count,
        }
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}", responses={404: {"description": "Ordres not found"}, 500: {"description": "Internal Server Error"}})
async def delete_ordres(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a single ordres by ID"""
    logger.debug(f"Deleting ordres with id: {id}")

    service = OrdresService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Ordres with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail=_NOT_FOUND_MSG)

        logger.info(f"Ordres {id} deleted successfully")
        return {"message": "Ordres deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting ordres {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
