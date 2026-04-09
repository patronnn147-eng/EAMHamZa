import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.ordres_intervention import Ordres_interventionService
from ..ordres_intervention.schemas import (
    Ordres_interventionData,
    Ordres_interventionUpdateData,
    Ordres_interventionResponse,
    Ordres_interventionListResponse,
    Ordres_interventionBatchCreateRequest,
    Ordres_interventionBatchUpdateRequest,
    Ordres_interventionBatchDeleteRequest,
)

router = APIRouter(prefix="/api/v1/entities/ordres_intervention", tags=["ordres_intervention"])
logger = logging.getLogger(__name__)


@router.get("", response_model=Ordres_interventionListResponse)
async def query_ordres_interventions(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    logger.debug(f"Querying ordres_interventions: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Ordres_interventionService(db)
    try:
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
    logger.debug(f"Querying ordres_interventions: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Ordres_interventionService(db)
    try:
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
    logger.debug(f"Creating new ordres_intervention with data: {data}")
    
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


@router.post("/batch", response_model=list[Ordres_interventionResponse], status_code=201)
async def create_ordres_interventions_batch(
    request: Ordres_interventionBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
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


@router.put("/batch", response_model=list[Ordres_interventionResponse])
async def update_ordres_interventions_batch(
    request: Ordres_interventionBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    logger.debug(f"Batch updating {len(request.items)} ordres_interventions")
    
    service = Ordres_interventionService(db)
    results = []
    
    try:
        for item in request.items:
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
    logger.debug(f"Updating ordres_intervention {id} with data: {data}")

    service = Ordres_interventionService(db)
    try:
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


@router.delete("/batch")
async def delete_ordres_interventions_batch(
    request: Ordres_interventionBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
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
