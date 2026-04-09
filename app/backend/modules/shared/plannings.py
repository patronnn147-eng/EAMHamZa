import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.plannings import PlanningsService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/plannings", tags=["plannings"])


# ---------- Pydantic Schemas ----------
class PlanningsData(BaseModel):
    """Entity data schema (for create/update)"""
    identifiant_planning: str
    date_debut: datetime
    date_fin: datetime
    type: str
    shift_type: Optional[str] = None
    chef_operation_id: Optional[int] = None
    chef_technique_id: Optional[int] = None
    zone_travail: Optional[str] = None
    sous_zone: Optional[str] = None
    ordre: Optional[str] = None
    created_at: Optional[datetime] = None


class PlanningsUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    identifiant_planning: Optional[str] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    type: Optional[str] = None
    shift_type: Optional[str] = None
    chef_operation_id: Optional[int] = None
    chef_technique_id: Optional[int] = None
    zone_travail: Optional[str] = None
    sous_zone: Optional[str] = None
    ordre: Optional[str] = None
    created_at: Optional[datetime] = None


class PlanningsResponse(BaseModel):
    """Entity response schema"""
    id: int
    identifiant_planning: str
    date_debut: datetime
    date_fin: datetime
    type: str
    shift_type: Optional[str] = None
    chef_operation_id: Optional[int] = None
    chef_technique_id: Optional[int] = None
    zone_travail: Optional[str] = None
    sous_zone: Optional[str] = None
    ordre: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PlanningsListResponse(BaseModel):
    """List response schema"""
    items: List[PlanningsResponse]
    total: int
    skip: int
    limit: int


class PlanningsBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[PlanningsData]


class PlanningsBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: PlanningsUpdateData


class PlanningsBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[PlanningsBatchUpdateItem]


class PlanningsBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=PlanningsListResponse)
async def query_planningss(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query planningss with filtering, sorting, and pagination"""
    logger.debug(f"Querying planningss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = PlanningsService(db)
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
        logger.debug(f"Found {result['total']} planningss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying planningss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=PlanningsListResponse)
async def query_planningss_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query planningss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying planningss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = PlanningsService(db)
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
            sort=sort
        )
        logger.debug(f"Found {result['total']} planningss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying planningss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=PlanningsResponse)
async def get_plannings(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single plannings by ID"""
    logger.debug(f"Fetching plannings with id: {id}, fields={fields}")
    
    service = PlanningsService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Plannings with id {id} not found")
            raise HTTPException(status_code=404, detail="Plannings not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching plannings {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=PlanningsResponse, status_code=201)
async def create_plannings(
    data: PlanningsData,
    db: AsyncSession = Depends(get_db),
):
    """Create a new plannings"""
    logger.debug(f"Creating new plannings with data: {data}")
    
    service = PlanningsService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create plannings")
        
        logger.info(f"Plannings created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating plannings: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating plannings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[PlanningsResponse], status_code=201)
async def create_planningss_batch(
    request: PlanningsBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple planningss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} planningss")
    
    service = PlanningsService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} planningss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[PlanningsResponse])
async def update_planningss_batch(
    request: PlanningsBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple planningss in a single request"""
    logger.debug(f"Batch updating {len(request.items)} planningss")
    
    service = PlanningsService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} planningss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=PlanningsResponse)
async def update_plannings(
    id: int,
    data: PlanningsUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing plannings"""
    logger.debug(f"Updating plannings {id} with data: {data}")

    service = PlanningsService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Plannings with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Plannings not found")
        
        logger.info(f"Plannings {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating plannings {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating plannings {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_planningss_batch(
    request: PlanningsBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple planningss by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} planningss")
    
    service = PlanningsService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} planningss successfully")
        return {"message": f"Successfully deleted {deleted_count} planningss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_plannings(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single plannings by ID"""
    logger.debug(f"Deleting plannings with id: {id}")
    
    service = PlanningsService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Plannings with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Plannings not found")
        
        logger.info(f"Plannings {id} deleted successfully")
        return {"message": "Plannings deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting plannings {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")