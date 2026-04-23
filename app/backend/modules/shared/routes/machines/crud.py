import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_db
from models.utilisateurs import Utilisateurs
from services.audit import AuditService, AuditEntityType
from services.machines import MachinesService
from ..machines.schemas import (
    MachinesData,
    MachinesUpdateData,
    MachinesResponse,
    MachinesListResponse,
    MachinesBatchCreateRequest,
    MachinesBatchUpdateRequest,
    MachinesBatchDeleteRequest,
)

router = APIRouter(prefix="/api/v1/entities/machines", tags=["machines"])
logger = logging.getLogger(__name__)


@router.get("", response_model=MachinesListResponse)
async def query_machiness(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query machiness with filtering, sorting, and pagination"""
    logger.debug(f"Querying machiness: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = MachinesService(db)
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
        logger.debug(f"Found {result['total']} machiness")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying machiness: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=MachinesListResponse)
async def query_machiness_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    logger.debug(f"Querying machiness: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = MachinesService(db)
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
        logger.debug(f"Found {result['total']} machiness")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying machiness: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=MachinesResponse)
async def get_machines(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    logger.debug(f"Fetching machines with id: {id}, fields={fields}")

    service = MachinesService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Machines with id {id} not found")
            raise HTTPException(status_code=404, detail="Machines not found")

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching machines {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=MachinesResponse, status_code=201)
async def create_machines(
    data: MachinesData,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    logger.debug(f"Creating new machines with data: {data}")

    service = MachinesService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create machines")

        logger.info(f"Machines created successfully with id: {result.id}")

        try:
            await AuditService(db).log_create(
                entity_type=AuditEntityType.MACHINE,
                entity_id=result.id,
                new_values=data.model_dump(),
                user_id=current_user.id,
                user_name=current_user.nom,
                entity_name=getattr(result, "nom", None),
            )
        except Exception:
            logger.warning("Audit log failed for create machine %s", result.id)

        return result
    except ValueError as e:
        logger.error(f"Validation error creating machines: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating machines: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=list[MachinesResponse], status_code=201)
async def create_machiness_batch(
    request: MachinesBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    logger.debug(f"Batch creating {len(request.items)} machiness")

    service = MachinesService(db)
    results = []

    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
                try:
                    await AuditService(db).log_create(
                        entity_type=AuditEntityType.MACHINE,
                        entity_id=result.id,
                        new_values=item_data.model_dump(),
                        user_id=current_user.id,
                        user_name=current_user.nom,
                        entity_name=getattr(result, "nom", None),
                    )
                except Exception:
                    logger.warning("Audit log failed for batch create machine %s", result.id)

        logger.info(f"Batch created {len(results)} machiness successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=list[MachinesResponse])
async def update_machiness_batch(
    request: MachinesBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    logger.debug(f"Batch updating {len(request.items)} machiness")

    service = MachinesService(db)
    results = []

    try:
        for item in request.items:
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
                try:
                    await AuditService(db).log_update(
                        entity_type=AuditEntityType.MACHINE,
                        entity_id=item.id,
                        old_values={},
                        new_values=update_dict,
                        user_id=current_user.id,
                        user_name=current_user.nom,
                        entity_name=getattr(result, "nom", None),
                    )
                except Exception:
                    logger.warning("Audit log failed for batch update machine %s", item.id)

        logger.info(f"Batch updated {len(results)} machiness successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=MachinesResponse)
async def update_machines(
    id: int,
    data: MachinesUpdateData,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    logger.debug(f"Updating machines {id} with data: {data}")

    service = MachinesService(db)
    try:
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}

        old_entity = await service.get_by_id(id)
        old_values = {k: getattr(old_entity, k, None) for k in update_dict} if old_entity else {}

        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Machines with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Machines not found")

        logger.info(f"Machines {id} updated successfully")

        try:
            new_values = {k: getattr(result, k, None) for k in update_dict}
            await AuditService(db).log_update(
                entity_type=AuditEntityType.MACHINE,
                entity_id=id,
                old_values=old_values,
                new_values=new_values,
                user_id=current_user.id,
                user_name=current_user.nom,
                entity_name=getattr(result, "nom", None),
            )
        except Exception:
            logger.warning("Audit log failed for update machine %s", id)

        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating machines {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating machines {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_machiness_batch(
    request: MachinesBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    logger.debug(f"Batch deleting {len(request.ids)} machiness")

    service = MachinesService(db)
    deleted_count = 0

    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
                try:
                    await AuditService(db).log_delete(
                        entity_type=AuditEntityType.MACHINE,
                        entity_id=item_id,
                        user_id=current_user.id,
                        user_name=current_user.nom,
                    )
                except Exception:
                    logger.warning("Audit log failed for batch delete machine %s", item_id)

        logger.info(f"Batch deleted {deleted_count} machiness successfully")
        return {"message": f"Successfully deleted {deleted_count} machiness", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_machines(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    logger.debug(f"Deleting machines with id: {id}")

    service = MachinesService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Machines with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Machines not found")

        logger.info(f"Machines {id} deleted successfully")

        try:
            await AuditService(db).log_delete(
                entity_type=AuditEntityType.MACHINE,
                entity_id=id,
                user_id=current_user.id,
                user_name=current_user.nom,
            )
        except Exception:
            logger.warning("Audit log failed for delete machine %s", id)

        return {"message": "Machines deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting machines {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
