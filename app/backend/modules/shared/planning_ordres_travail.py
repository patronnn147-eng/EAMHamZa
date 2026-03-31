import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs, UserRole
from models.planning_utilisateurs import Planning_utilisateurs
from models.plannings import Plannings
from sqlalchemy import select, or_
from services.planning_ordres_travail import Planning_ordres_travailService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/planning_ordres_travail", tags=["planning_ordres_travail"])


# ---------- Pydantic Schemas ----------
class Planning_ordres_travailData(BaseModel):
    """Entity data schema (for create/update)"""
    planning_id: int
    ordre_travail_id: Optional[int] = None
    created_at: Optional[datetime] = None


class Planning_ordres_travailUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    planning_id: Optional[int] = None
    ordre_travail_id: Optional[int] = None
    created_at: Optional[datetime] = None


class Planning_ordres_travailResponse(BaseModel):
    """Entity response schema"""
    id: int
    planning_id: int
    ordre_travail_id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Planning_ordres_travailListResponse(BaseModel):
    """List response schema"""
    items: List[Planning_ordres_travailResponse]
    total: int
    skip: int
    limit: int


class Planning_ordres_travailBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Planning_ordres_travailData]


class Planning_ordres_travailBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Planning_ordres_travailUpdateData


class Planning_ordres_travailBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Planning_ordres_travailBatchUpdateItem]


class Planning_ordres_travailBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Planning_ordres_travailListResponse)
async def query_planning_ordres_travails(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query planning_ordres_travails with filtering, sorting, and pagination"""
    logger.debug(f"User {current_user.email} querying planning_ordres_travails: query={query}, sort={sort}, skip={skip}, limit={limit}")
    
    service = Planning_ordres_travailService(db)
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
        logger.debug(f"Found {result['total']} planning_ordres_travails")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying planning_ordres_travails: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Planning_ordres_travailListResponse)
async def query_planning_ordres_travails_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Query planning_ordres_travails with filtering, sorting, and pagination without user limitation
    logger.debug(f"User {current_user.email} querying all planning_ordres_travails: query={query}, sort={sort}, skip={skip}, limit={limit}")

    service = Planning_ordres_travailService(db)
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
        logger.debug(f"Found {result['total']} planning_ordres_travails")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying planning_ordres_travails: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Planning_ordres_travailResponse)
async def get_planning_ordres_travail(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single planning_ordres_travail by ID"""
    logger.debug(f"Fetching planning_ordres_travail with id: {id}, fields={fields}")
    
    service = Planning_ordres_travailService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Planning_ordres_travail with id {id} not found")
            raise HTTPException(status_code=404, detail="Planning_ordres_travail not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching planning_ordres_travail {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Planning_ordres_travailResponse, status_code=201)
async def create_planning_ordres_travail(
    data: Planning_ordres_travailData,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new planning_ordres_travail with role-based access control"""
    logger.debug(f"Creating new planning_ordres_travail with data: {data}")
    
    # Check if user has access to this planning
    if current_user.role != UserRole.ADMIN:
        # Fetch the planning to check roles
        planning_query = select(Plannings).where(Plannings.id == data.planning_id)
        planning_result = await db.execute(planning_query)
        planning = planning_result.scalar_one_or_none()

        if not planning:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Planning not found"
            )

        has_access = False
        if current_user.role == UserRole.CHEFOP:
            has_access = planning.chef_operation_id == current_user.id
        elif current_user.role == UserRole.CHEFTECH:
            has_access = planning.chef_technique_id == current_user.id
        
        # If not responsible, check if explicitly assigned (bridge table)
        if not has_access:
            assignment_query = select(Planning_utilisateurs).where(
                Planning_utilisateurs.planning_id == data.planning_id,
                Planning_utilisateurs.utilisateur_id == current_user.id,
            )
            assignment_result = await db.execute(assignment_query)
            assignment = assignment_result.scalar_one_or_none()
            has_access = assignment is not None
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to link work orders to this planning",
            )
    
    service = Planning_ordres_travailService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create planning_ordres_travail")
        
        logger.info(f"Planning_ordres_travail created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating planning_ordres_travail: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating planning_ordres_travail: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Planning_ordres_travailResponse], status_code=201)
async def create_planning_ordres_travails_batch(
    request: Planning_ordres_travailBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple planning_ordres_travails in a single request"""
    logger.debug(f"Batch creating {len(request.items)} planning_ordres_travails")
    
    service = Planning_ordres_travailService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} planning_ordres_travails successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Planning_ordres_travailResponse])
async def update_planning_ordres_travails_batch(
    request: Planning_ordres_travailBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple planning_ordres_travails in a single request"""
    logger.debug(f"Batch updating {len(request.items)} planning_ordres_travails")
    
    service = Planning_ordres_travailService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} planning_ordres_travails successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Planning_ordres_travailResponse)
async def update_planning_ordres_travail(
    id: int,
    data: Planning_ordres_travailUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing planning_ordres_travail"""
    logger.debug(f"Updating planning_ordres_travail {id} with data: {data}")

    service = Planning_ordres_travailService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Planning_ordres_travail with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Planning_ordres_travail not found")
        
        logger.info(f"Planning_ordres_travail {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating planning_ordres_travail {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating planning_ordres_travail {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_planning_ordres_travails_batch(
    request: Planning_ordres_travailBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple planning_ordres_travails by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} planning_ordres_travails")
    
    service = Planning_ordres_travailService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} planning_ordres_travails successfully")
        return {"message": f"Successfully deleted {deleted_count} planning_ordres_travails", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_planning_ordres_travail(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single planning_ordres_travail by ID"""
    logger.debug(f"Deleting planning_ordres_travail with id: {id}")
    
    service = Planning_ordres_travailService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Planning_ordres_travail with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Planning_ordres_travail not found")
        
        logger.info(f"Planning_ordres_travail {id} deleted successfully")
        return {"message": "Planning_ordres_travail deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting planning_ordres_travail {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")