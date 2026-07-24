import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_db
from models.utilisateurs import Utilisateurs
from services.audit import AuditService, AuditEntityType
from services.ordres_intervention import OrdresInterventionService
from .schemas import (
    OrdresInterventionData,
    OrdresInterventionUpdateData,
    OrdresInterventionResponse,
    OrdresInterventionListResponse,
    OrdresInterventionBatchCreateRequest,
    OrdresInterventionBatchUpdateRequest,
    OrdresInterventionBatchDeleteRequest,
)
from typing import Annotated

router = APIRouter(
    prefix="/api/v1/entities/ordres_intervention", tags=["OrdresIntervention"]
)
logger = logging.getLogger(__name__)

_NOT_FOUND_MSG = "OrdresIntervention not found"


@router.get("", response_model=OrdresInterventionListResponse, responses={400: {"description": "Invalid query JSON format"}, 500: {"description": "Internal Server Error"}})
async def query_OrdresInterventions(
    *, query: Annotated[str, Query(description="Query conditions (JSON string)")] = None,
    sort: Annotated[str, Query(description="Sort field (prefix with '-' for descending)")] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(
        ge=1, le=2000, description="Max number of records to return"
    )] = 20,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    logger.debug(
        f"Querying OrdresInterventions: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}"
    )

    service = OrdresInterventionService(db)
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
        logger.debug(f"Found {result['total']} OrdresInterventions")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error querying OrdresInterventions: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=OrdresInterventionListResponse, responses={400: {"description": "Invalid query JSON format"}, 500: {"description": "Internal Server Error"}})
async def query_OrdresInterventions_all(
    *, query: Annotated[str, Query(description="Query conditions (JSON string)")] = None,
    sort: Annotated[str, Query(description="Sort field (prefix with '-' for descending)")] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(
        ge=1, le=2000, description="Max number of records to return"
    )] = 20,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    logger.debug(
        f"Querying OrdresInterventions: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}"
    )

    service = OrdresInterventionService(db)
    try:
        query_dict = None
        if query:
            try:
                query_dict = json.loads(query)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid query JSON format")

        result = await service.get_list(
            skip=skip, limit=limit, query_dict=query_dict, sort=sort
        )
        logger.debug(f"Found {result['total']} OrdresInterventions")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error querying OrdresInterventions: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=OrdresInterventionResponse, responses={404: {"description": "OrdresIntervention not found"}, 500: {"description": "Internal Server Error"}})
async def get_OrdresIntervention(
    *, id: int,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    logger.debug(f"Fetching OrdresIntervention with id: {id}, fields={fields}")

    service = OrdresInterventionService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"OrdresIntervention with id {id} not found")
            raise HTTPException(status_code=404, detail=_NOT_FOUND_MSG)

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error fetching OrdresIntervention {id}: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=OrdresInterventionResponse, status_code=201, responses={400: {"description": "Failed to create OrdresIntervention"}, 500: {"description": "Internal Server Error"}})
async def create_OrdresIntervention(
    data: OrdresInterventionData,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    logger.debug(f"Creating new OrdresIntervention with data: {data}")

    data.statut = "EN_ATTENTE"
    data.requested_at = datetime.now()

    service = OrdresInterventionService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(
                status_code=400, detail="Failed to create OrdresIntervention"
            )

        safe_id = str(result.id).replace("\r", "").replace("\n", "")
        logger.info(f"OrdresIntervention created successfully with id: {safe_id}")

        try:
            await AuditService(db).log_create(
                entity_type=AuditEntityType.INTERVENTION,
                entity_id=result.id,
                new_values=data.model_dump(mode="json"),
                user_id=current_user.id,
                user_name=current_user.nom,
                entity_name=getattr(result, "titre", None),
            )
        except Exception:
            logger.warning("Audit log failed for create intervention %s", safe_id)

        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.exception(f"Validation error creating OrdresIntervention: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error creating OrdresIntervention: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/batch", response_model=list[OrdresInterventionResponse], status_code=201, 
responses={500: {"description": "Internal Server Error"}})
async def create_OrdresInterventions_batch(
    request: OrdresInterventionBatchCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    logger.debug(f"Batch creating {len(request.items)} OrdresInterventions")

    service = OrdresInterventionService(db)
    results = []

    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
                safe_item_id = str(result.id).replace("\r", "").replace("\n", "")
                try:
                    await AuditService(db).log_create(
                        entity_type=AuditEntityType.INTERVENTION,
                        entity_id=result.id,
                        new_values=item_data.model_dump(mode="json"),
                        user_id=current_user.id,
                        user_name=current_user.nom,
                        entity_name=getattr(result, "titre", None),
                    )
                except Exception:
                    logger.warning(
                        "Audit log failed for batch create intervention %s", safe_item_id
                    )

        logger.info(f"Batch created {len(results)} OrdresInterventions successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=list[OrdresInterventionResponse], responses={500: {"description": "Internal Server Error"}})
async def update_OrdresInterventions_batch(
    request: OrdresInterventionBatchUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    logger.debug(f"Batch updating {len(request.items)} OrdresInterventions")

    service = OrdresInterventionService(db)
    results = []

    try:
        for item in request.items:
            update_dict = {
                k: v for k, v in item.updates.model_dump().items() if v is not None
            }
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
                try:
                    await AuditService(db).log_update(
                        entity_type=AuditEntityType.INTERVENTION,
                        entity_id=item.id,
                        old_values={},
                        new_values=update_dict,
                        user_id=current_user.id,
                        user_name=current_user.nom,
                        entity_name=getattr(result, "titre", None),
                    )
                except Exception:
                    logger.warning(
                        "Audit log failed for batch update intervention %s", item.id
                    )

        logger.info(f"Batch updated {len(results)} OrdresInterventions successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=OrdresInterventionResponse, responses={400: {"description": "Bad Request"}, 404: {"description": "OrdresIntervention not found"}, 500: {"description": "Internal Server Error"}})
async def update_OrdresIntervention(
    id: int,
    data: OrdresInterventionUpdateData,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    logger.debug(f"Updating OrdresIntervention {id} with data: {data}")

    service = OrdresInterventionService(db)
    try:
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}

        old_entity = await service.get_by_id(id)
        old_values = (
            {k: getattr(old_entity, k, None) for k in update_dict} if old_entity else {}
        )

        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"OrdresIntervention with id {id} not found for update")
            raise HTTPException(status_code=404, detail=_NOT_FOUND_MSG)

        logger.info(f"OrdresIntervention {id} updated successfully")

        try:
            new_values = {k: getattr(result, k, None) for k in update_dict}
            await AuditService(db).log_update(
                entity_type=AuditEntityType.INTERVENTION,
                entity_id=id,
                old_values=old_values,
                new_values=new_values,
                user_id=current_user.id,
                user_name=current_user.nom,
                entity_name=getattr(result, "titre", None),
            )
        except Exception:
            logger.warning("Audit log failed for update intervention %s", id)

        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.exception(
            f"Validation error updating OrdresIntervention {id}: {str(e)}"
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(
            f"Error updating OrdresIntervention {id}: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch", responses={500: {"description": "Internal Server Error"}})
async def delete_OrdresInterventions_batch(
    request: OrdresInterventionBatchDeleteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    logger.debug(f"Batch deleting {len(request.ids)} OrdresInterventions")

    service = OrdresInterventionService(db)
    deleted_count = 0

    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
                try:
                    await AuditService(db).log_delete(
                        entity_type=AuditEntityType.INTERVENTION,
                        entity_id=item_id,
                        user_id=current_user.id,
                        user_name=current_user.nom,
                    )
                except Exception:
                    logger.warning(
                        "Audit log failed for batch delete intervention %s", item_id
                    )

        logger.info(f"Batch deleted {deleted_count} OrdresInterventions successfully")
        return {
            "message": f"Successfully deleted {deleted_count} OrdresInterventions",
            "deleted_count": deleted_count,
        }
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}", responses={404: {"description": "OrdresIntervention not found"}, 500: {"description": "Internal Server Error"}})
async def delete_OrdresIntervention(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    logger.debug(f"Deleting OrdresIntervention with id: {id}")

    service = OrdresInterventionService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"OrdresIntervention with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail=_NOT_FOUND_MSG)

        logger.info(f"OrdresIntervention {id} deleted successfully")

        try:
            await AuditService(db).log_delete(
                entity_type=AuditEntityType.INTERVENTION,
                entity_id=id,
                user_id=current_user.id,
                user_name=current_user.nom,
            )
        except Exception:
            logger.warning("Audit log failed for delete intervention %s", id)

        return {"message": "OrdresIntervention deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error deleting OrdresIntervention {id}: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
