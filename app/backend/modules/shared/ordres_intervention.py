import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.auth import require_role
from models.utilisateurs import Utilisateurs
from services.ordres_intervention import Ordres_interventionService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/ordres_intervention", tags=["ordres_intervention"])


# ---------- Pydantic Schemas ----------
class Ordres_interventionData(BaseModel):
    """Entity data schema (for create/update)"""
    date_intervention: datetime
    rapport: str = None
    ordre_travail_id: Optional[int] = None
    technicien_id: Optional[int] = None
    statut: Optional[str] = None
    problem_description: Optional[str] = None
    priority: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
    required_materials: Optional[str] = None
    machine_id: Optional[int] = None
    requested_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    created_at: Optional[datetime] = None
    actual_failure_type: Optional[str] = None
    ml_prediction_matched: Optional[bool] = None


class Ordres_interventionUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    date_intervention: Optional[datetime] = None
    rapport: Optional[str] = None
    ordre_travail_id: Optional[int] = None
    technicien_id: Optional[int] = None
    statut: Optional[str] = None
    problem_description: Optional[str] = None
    priority: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
    required_materials: Optional[str] = None
    machine_id: Optional[int] = None
    requested_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    created_at: Optional[datetime] = None
    actual_failure_type: Optional[str] = None
    ml_prediction_matched: Optional[bool] = None


class Ordres_interventionResponse(BaseModel):
    """Entity response schema"""
    id: int
    date_intervention: datetime
    rapport: Optional[str] = None
    ordre_travail_id: Optional[int] = None
    technicien_id: Optional[int] = None
    statut: Optional[str] = None
    problem_description: Optional[str] = None
    priority: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
    required_materials: Optional[str] = None
    machine_id: Optional[int] = None
    requested_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    created_at: Optional[datetime] = None
    actual_failure_type: Optional[str] = None
    ml_prediction_matched: Optional[bool] = None

    class Config:
        from_attributes = True

class Ordres_interventionValidationData(BaseModel):
    action: str  # "APPROVE" or "REJECT"
    technicien_id: Optional[int] = None  # Technician to assign
    rejection_reason: Optional[str] = None


class Ordres_interventionListResponse(BaseModel):
    """List response schema"""
    items: List[Ordres_interventionResponse]
    total: int
    skip: int
    limit: int


class Ordres_interventionBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Ordres_interventionData]


class Ordres_interventionBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Ordres_interventionUpdateData


class Ordres_interventionBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Ordres_interventionBatchUpdateItem]


class Ordres_interventionBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Ordres_interventionListResponse)
async def query_ordres_interventions(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query ordres_interventions with filtering, sorting, and pagination"""
    logger.debug(f"Querying ordres_interventions: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Ordres_interventionService(db)
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
        logger.debug(f"Found {result['total']} ordres_interventions")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying ordres_interventions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Ordres_interventionListResponse)
async def query_ordres_interventions_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query ordres_interventions with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying ordres_interventions: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Ordres_interventionService(db)
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
        logger.debug(f"Found {result['total']} ordres_interventions")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying ordres_interventions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Ordres_interventionResponse)
async def get_ordres_intervention(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single ordres_intervention by ID"""
    logger.debug(f"Fetching ordres_intervention with id: {id}, fields={fields}")
    
    service = Ordres_interventionService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Ordres_intervention with id {id} not found")
            raise HTTPException(status_code=404, detail="Ordres_intervention not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching ordres_intervention {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Ordres_interventionResponse, status_code=201)
async def create_ordres_intervention(
    data: Ordres_interventionData,
    db: AsyncSession = Depends(get_db),
):
    """Create a new ordres_intervention"""
    logger.debug(f"Creating new ordres_intervention with data: {data}")
    
    # Enforce default status
    data.statut = "EN_ATTENTE"
    data.requested_at = datetime.now()
    
    service = Ordres_interventionService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create ordres_intervention")
        
        logger.info(f"Ordres_intervention created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating ordres_intervention: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating ordres_intervention: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Ordres_interventionResponse], status_code=201)
async def create_ordres_interventions_batch(
    request: Ordres_interventionBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple ordres_interventions in a single request"""
    logger.debug(f"Batch creating {len(request.items)} ordres_interventions")
    
    service = Ordres_interventionService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} ordres_interventions successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Ordres_interventionResponse])
async def update_ordres_interventions_batch(
    request: Ordres_interventionBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple ordres_interventions in a single request"""
    logger.debug(f"Batch updating {len(request.items)} ordres_interventions")
    
    service = Ordres_interventionService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} ordres_interventions successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Ordres_interventionResponse)
async def update_ordres_intervention(
    id: int,
    data: Ordres_interventionUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing ordres_intervention"""
    logger.debug(f"Updating ordres_intervention {id} with data: {data}")

    service = Ordres_interventionService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Ordres_intervention with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Ordres_intervention not found")
        
        logger.info(f"Ordres_intervention {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating ordres_intervention {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating ordres_intervention {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/{id}/validate", response_model=Ordres_interventionResponse)
async def validate_ordres_intervention(
    id: int,
    data: Ordres_interventionValidationData,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(require_role(["CHEFTECH"]))
):
    """Validate or reject an Intervention (CHEFTECH only)"""
    logger.debug(f"Validating ordres_intervention {id} with action: {data.action}")
    service = Ordres_interventionService(db)
    
    intervention = await service.get_by_id(id)
    if not intervention:
        raise HTTPException(status_code=404, detail="Ordres_intervention not found")
        
    update_dict = {}
    if data.action == "APPROVE":
        update_dict["statut"] = "ACCEPTED"
        update_dict["approved_by"] = current_user.id
        update_dict["approved_at"] = datetime.now()
        
        # Create a linked Work Order
        try:
            from services.ordres_travail import Ordres_travailService
            
            wo_service = Ordres_travailService(db)
            
            # Check if machine_id is available, it's required for work orders
            if not intervention.machine_id:
                raise HTTPException(status_code=400, detail="Cannot create Work Order: Intervention must be associated with a machine.")
            
            new_wo = await wo_service.create({
                "titre": f"[Intervention Acceptée] Demande #{id}",
                "description": intervention.problem_description or "Demande d'intervention validée par le ChefTech",
                "priorite": intervention.priority or "MOYENNE",
                "statut": "EN_ATTENTE", # Still needs technician assignment later
                "machine_id": intervention.machine_id,
                "created_by": intervention.technicien_id, # Can be whoever created it
            })
            
            update_dict["ordre_travail_id"] = new_wo.id
            logger.info(f"Created linked Work Order #{new_wo.id} for Intervention #{id}")
        except Exception as e:
            logger.error(f"Failed to create linked Work Order for accepted intervention #{id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to create linked Work Order.")

    elif data.action == "REJECT":
        update_dict["statut"] = "REJETE"
        update_dict["approved_by"] = current_user.id
        update_dict["approved_at"] = datetime.now()
        update_dict["rejection_reason"] = data.rejection_reason
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
        
    result = await service.update(id, update_dict)
    return result


@router.delete("/batch")
async def delete_ordres_interventions_batch(
    request: Ordres_interventionBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple ordres_interventions by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} ordres_interventions")
    
    service = Ordres_interventionService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} ordres_interventions successfully")
        return {"message": f"Successfully deleted {deleted_count} ordres_interventions", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_ordres_intervention(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single ordres_intervention by ID"""
    logger.debug(f"Deleting ordres_intervention with id: {id}")
    
    service = Ordres_interventionService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Ordres_intervention with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Ordres_intervention not found")
        
        logger.info(f"Ordres_intervention {id} deleted successfully")
        return {"message": "Ordres_intervention deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting ordres_intervention {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")