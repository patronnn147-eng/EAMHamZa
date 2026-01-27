import json
import logging
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.utilisateurs import UtilisateursService
from dependencies.auth import get_current_user
from schemas.auth import UserResponse

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/utilisateurs", tags=["utilisateurs"])


# ---------- Pydantic Schemas ----------
class UtilisateursData(BaseModel):
    """Entity data schema (for create/update)"""
    identifiant: str
    nom_utilisateur: str
    mot_de_passe_chiffre: str
    courriel: str
    role: str
    created_at: Optional[datetime] = None


class UtilisateursUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    identifiant: Optional[str] = None
    nom_utilisateur: Optional[str] = None
    mot_de_passe_chiffre: Optional[str] = None
    courriel: Optional[str] = None
    role: Optional[str] = None
    created_at: Optional[datetime] = None


class UtilisateursResponse(BaseModel):
    """Entity response schema"""
    id: int
    identifiant: str
    nom_utilisateur: str
    mot_de_passe_chiffre: str
    courriel: str
    role: str
    user_id: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UtilisateursListResponse(BaseModel):
    """List response schema"""
    items: List[UtilisateursResponse]
    total: int
    skip: int
    limit: int


class UtilisateursBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[UtilisateursData]


class UtilisateursBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: UtilisateursUpdateData


class UtilisateursBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[UtilisateursBatchUpdateItem]


class UtilisateursBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=UtilisateursListResponse)
async def query_utilisateurss(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query utilisateurss with filtering, sorting, and pagination (user can only see their own records)"""
    logger.debug(f"Querying utilisateurss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = UtilisateursService(db)
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
            user_id=str(current_user.id),
        )
        logger.debug(f"Found {result['total']} utilisateurss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying utilisateurss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=UtilisateursListResponse)
async def query_utilisateurss_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query utilisateurss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying utilisateurss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = UtilisateursService(db)
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
        logger.debug(f"Found {result['total']} utilisateurss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying utilisateurss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=UtilisateursResponse)
async def get_utilisateurs(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single utilisateurs by ID (user can only see their own records)"""
    logger.debug(f"Fetching utilisateurs with id: {id}, fields={fields}")
    
    service = UtilisateursService(db)
    try:
        result = await service.get_by_id(id, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Utilisateurs with id {id} not found")
            raise HTTPException(status_code=404, detail="Utilisateurs not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching utilisateurs {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=UtilisateursResponse, status_code=201)
async def create_utilisateurs(
    data: UtilisateursData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new utilisateurs"""
    logger.debug(f"Creating new utilisateurs with data: {data}")
    
    service = UtilisateursService(db)
    try:
        result = await service.create(data.model_dump(), user_id=str(current_user.id))
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create utilisateurs")
        
        logger.info(f"Utilisateurs created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating utilisateurs: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating utilisateurs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[UtilisateursResponse], status_code=201)
async def create_utilisateurss_batch(
    request: UtilisateursBatchCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple utilisateurss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} utilisateurss")
    
    service = UtilisateursService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump(), user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} utilisateurss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[UtilisateursResponse])
async def update_utilisateurss_batch(
    request: UtilisateursBatchUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update multiple utilisateurss in a single request (requires ownership)"""
    logger.debug(f"Batch updating {len(request.items)} utilisateurss")
    
    service = UtilisateursService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict, user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} utilisateurss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=UtilisateursResponse)
async def update_utilisateurs(
    id: int,
    data: UtilisateursUpdateData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing utilisateurs (requires ownership)"""
    logger.debug(f"Updating utilisateurs {id} with data: {data}")

    service = UtilisateursService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Utilisateurs with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Utilisateurs not found")
        
        logger.info(f"Utilisateurs {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating utilisateurs {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating utilisateurs {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_utilisateurss_batch(
    request: UtilisateursBatchDeleteRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple utilisateurss by their IDs (requires ownership)"""
    logger.debug(f"Batch deleting {len(request.ids)} utilisateurss")
    
    service = UtilisateursService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id, user_id=str(current_user.id))
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} utilisateurss successfully")
        return {"message": f"Successfully deleted {deleted_count} utilisateurss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_utilisateurs(
    id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single utilisateurs by ID (requires ownership)"""
    logger.debug(f"Deleting utilisateurs with id: {id}")
    
    service = UtilisateursService(db)
    try:
        success = await service.delete(id, user_id=str(current_user.id))
        if not success:
            logger.warning(f"Utilisateurs with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Utilisateurs not found")
        
        logger.info(f"Utilisateurs {id} deleted successfully")
        return {"message": "Utilisateurs deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting utilisateurs {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")