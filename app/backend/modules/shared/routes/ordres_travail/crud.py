import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_db
from models.utilisateurs import Utilisateurs
from services.audit import AuditService, AuditEntityType
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
from typing import Annotated

router = APIRouter(prefix="/api/v1/entities/ordres_travail", tags=["ordres_travail"])
logger = logging.getLogger(__name__)


@router.get("", response_model=Ordres_travailListResponse, responses={400: {"description": "Invalid query JSON format"}, 500: {"description": "Internal Server Error"}})
async def query_ordres_travails(
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
        f"Querying ordres_travails: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}"
    )

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
        logger.exception(f"Error querying ordres_travails: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Ordres_travailListResponse, responses={400: {"description": "Invalid query JSON format"}, 500: {"description": "Internal Server Error"}})
async def query_ordres_travails_all(
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
        f"Querying ordres_travails: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}"
    )

    service = Ordres_travailService(db)
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
        logger.debug(f"Found {result['total']} ordres_travails")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error querying ordres_travails: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Ordres_travailResponse, responses={404: {"description": "Ordres_travail not found"}, 500: {"description": "Internal Server Error"}})
async def get_ordres_travail(
    *, id: int,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
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
        logger.exception(f"Error fetching ordres_travail {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Ordres_travailResponse, status_code=201, responses={400: {"description": "Failed to create ordres_travail"}, 500: {"description": "Internal Server Error"}})
async def create_ordres_travail(
    data: Ordres_travailData,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    logger.debug(f"Creating new ordres_travail with data: {data}")

    data.statut = "EN_ATTENTE"

    service = Ordres_travailService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(
                status_code=400, detail="Failed to create ordres_travail"
            )

        safe_id = str(result.id).replace("\r", "").replace("\n", "")
        logger.info(f"Ordres_travail created successfully with id: {safe_id}")

        try:
            await AuditService(db).log_create(
                entity_type=AuditEntityType.WORK_ORDER,
                entity_id=result.id,
                new_values=data.model_dump(),
                user_id=current_user.id,
                user_name=current_user.nom,
                entity_name=getattr(result, "titre", None),
            )
        except Exception:
            logger.warning("Audit log failed for create work order %s", result.id)

        return result
    except ValueError as e:
        logger.exception(f"Validation error creating ordres_travail: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error creating ordres_travail: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=list[Ordres_travailResponse], status_code=201, responses={500: {"description": "Internal Server Error"}})
async def create_ordres_travails_batch(
    request: Ordres_travailBatchCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    logger.debug(f"Batch creating {len(request.items)} ordres_travails")

    service = Ordres_travailService(db)
    results = []

    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
                try:
                    await AuditService(db).log_create(
                        entity_type=AuditEntityType.WORK_ORDER,
                        entity_id=result.id,
                        new_values=item_data.model_dump(),
                        user_id=current_user.id,
                        user_name=current_user.nom,
                        entity_name=getattr(result, "titre", None),
                    )
                except Exception:
                    logger.warning(
                        "Audit log failed for batch create work order %s", result.id
                    )

        logger.info(f"Batch created {len(results)} ordres_travails successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=list[Ordres_travailResponse], responses={500: {"description": "Internal Server Error"}})
async def update_ordres_travails_batch(
    request: Ordres_travailBatchUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    logger.debug(f"Batch updating {len(request.items)} ordres_travails")

    service = Ordres_travailService(db)
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
                        entity_type=AuditEntityType.WORK_ORDER,
                        entity_id=item.id,
                        old_values={},
                        new_values=update_dict,
                        user_id=current_user.id,
                        user_name=current_user.nom,
                        entity_name=getattr(result, "titre", None),
                    )
                except Exception:
                    logger.warning(
                        "Audit log failed for batch update work order %s", item.id
                    )

        logger.info(f"Batch updated {len(results)} ordres_travails successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Ordres_travailResponse, responses={400: {"description": "Bad Request"}, 404: {"description": "Ordres_travail not found"}, 500: {"description": "Internal Server Error"}})
async def update_ordres_travail(
    id: int,
    data: Ordres_travailUpdateData,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    logger.debug(f"Updating ordres_travail {id} with data: {data}")

    service = Ordres_travailService(db)
    try:
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}

        old_entity = await service.get_by_id(id)
        old_values = (
            {k: getattr(old_entity, k, None) for k in update_dict} if old_entity else {}
        )

        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Ordres_travail with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Ordres_travail not found")

        logger.info(f"Ordres_travail {id} updated successfully")

        try:
            new_values = {k: getattr(result, k, None) for k in update_dict}
            await AuditService(db).log_update(
                entity_type=AuditEntityType.WORK_ORDER,
                entity_id=id,
                old_values=old_values,
                new_values=new_values,
                user_id=current_user.id,
                user_name=current_user.nom,
                entity_name=getattr(result, "titre", None),
            )
        except Exception:
            logger.warning("Audit log failed for update work order %s", id)

        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.exception(f"Validation error updating ordres_travail {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error updating ordres_travail {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch", responses={500: {"description": "Internal Server Error"}})
async def delete_ordres_travails_batch(
    request: Ordres_travailBatchDeleteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    logger.debug(f"Batch deleting {len(request.ids)} ordres_travails")

    service = Ordres_travailService(db)
    deleted_count = 0

    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
                try:
                    await AuditService(db).log_delete(
                        entity_type=AuditEntityType.WORK_ORDER,
                        entity_id=item_id,
                        user_id=current_user.id,
                        user_name=current_user.nom,
                    )
                except Exception:
                    logger.warning(
                        "Audit log failed for batch delete work order %s", item_id
                    )

        logger.info(f"Batch deleted {deleted_count} ordres_travails successfully")
        return {
            "message": f"Successfully deleted {deleted_count} ordres_travails",
            "deleted_count": deleted_count,
        }
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}", responses={404: {"description": "Ordres_travail not found"}, 500: {"description": "Internal Server Error"}})
async def delete_ordres_travail(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    logger.debug(f"Deleting ordres_travail with id: {id}")

    service = Ordres_travailService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Ordres_travail with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Ordres_travail not found")

        logger.info(f"Ordres_travail {id} deleted successfully")

        try:
            await AuditService(db).log_delete(
                entity_type=AuditEntityType.WORK_ORDER,
                entity_id=id,
                user_id=current_user.id,
                user_name=current_user.nom,
            )
        except Exception:
            logger.warning("Audit log failed for delete work order %s", id)

        return {"message": "Ordres_travail deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting ordres_travail {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
