import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.ordres_travail import Ordres_travailService
from ..ordres_travail.schemas import (
    Ordres_travailData,
    Ordres_travailUpdateData,
    Ordres_travailResponse,
    Ordres_travailListResponse,
    Ordres_travailBatchCreateRequest,
    Ordres_travailBatchUpdateRequest,
    Ordres_travailBatchDeleteRequest,
)

router = APIRouter(prefix="/api/v1/entities/ordres_travail", tags=["ordres_travail"])
logger = logging.getLogger(__name__)


@router.get("", response_model=Ordres_travailListResponse)
async def query_ordres_travails(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    logger.debug(f"Querying ordres_travails: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Ordres_travailService(db)
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
        logger.debug(f"Found {result['total']} ordres_travails")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying ordres_travails: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Ordres_travailListResponse)
async def query_ordres_travails_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    logger.debug(f"Querying ordres_travails: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Ordres_travailService(db)
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
        logger.debug(f"Found {result['total']} ordres_travails")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying ordres_travails: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Ordres_travailResponse)
async def get_ordres_travail(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    logger.debug(f"Fetching ordres_travail with id: {id}, fields={fields}")
    
    service = Ordres_travailService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Ordres_travail with id {id} not found")
            raise HTTPException(status_code=404, detail="Ordres_travail not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching ordres_travail {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Ordres_travailResponse, status_code=201)
async def create_ordres_travail(
    data: Ordres_travailData,
    db: AsyncSession = Depends(get_db),
):
    logger.debug(f"Creating new ordres_travail with data: {data}")
    
    data.statut = "EN_ATTENTE"
    
    service = Ordres_travailService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create ordres_travail")
        
        logger.info(f"Ordres_travail created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating ordres_travail: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating ordres_travail: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=list[Ordres_travailResponse], status_code=201)
async def create_ordres_travails_batch(
    request: Ordres_travailBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    logger.debug(f"Batch creating {len(request.items)} ordres_travails")
    
    service = Ordres_travailService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} ordres_travails successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=list[Ordres_travailResponse])
async def update_ordres_travails_batch(
    request: Ordres_travailBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    logger.debug(f"Batch updating {len(request.items)} ordres_travails")
    
    service = Ordres_travailService(db)
    results = []
    
    try:
        for item in request.items:
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} ordres_travails successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Ordres_travailResponse)
async def update_ordres_travail(
    id: int,
    data: Ordres_travailUpdateData,
    db: AsyncSession = Depends(get_db),
):
    logger.debug(f"Updating ordres_travail {id} with data: {data}")

    service = Ordres_travailService(db)
    try:
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Ordres_travail with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Ordres_travail not found")
        
        logger.info(f"Ordres_travail {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating ordres_travail {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating ordres_travail {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_ordres_travails_batch(
    request: Ordres_travailBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    logger.debug(f"Batch deleting {len(request.ids)} ordres_travails")
    
    service = Ordres_travailService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} ordres_travails successfully")
        return {"message": f"Successfully deleted {deleted_count} ordres_travails", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_ordres_travail(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    logger.debug(f"Deleting ordres_travail with id: {id}")
    
    service = Ordres_travailService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Ordres_travail with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Ordres_travail not found")
        
        logger.info(f"Ordres_travail {id} deleted successfully")
        return {"message": "Ordres_travail deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting ordres_travail {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
