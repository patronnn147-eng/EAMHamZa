import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs, UserRole
from models.planning_utilisateurs import PlanningUtilisateurs
from models.plannings import Plannings
from services.planning_ordres_travail import PlanningOrdresTravailService
from .schemas import (
    PlanningOrdresTravailData,
    PlanningOrdresTravailUpdateData,
    PlanningOrdresTravailResponse,
    PlanningOrdresTravailListResponse,
    PlanningOrdresTravailBatchCreateRequest,
    PlanningOrdresTravailBatchUpdateRequest,
    PlanningOrdresTravailBatchDeleteRequest,
)
from typing import Annotated

router = APIRouter(
    prefix="/api/v1/entities/planning_OrdresTravail", tags=["planning_OrdresTravail"]
)
logger = logging.getLogger(__name__)

_NOT_FOUND_MSG = "PlanningOrdresTravail not found"


@router.get("", response_model=PlanningOrdresTravailListResponse, responses={400: {"description": "Invalid query JSON format"}, 500: {"description": "Internal Server Error"}})
async def query_planning_OrdresTravails(
    *, query: Annotated[str, Query(description="Query conditions (JSON string)")] = None,
    sort: Annotated[str, Query(description="Sort field (prefix with '-' for descending)")] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(
        ge=1, le=2000, description="Max number of records to return"
    )] = 20,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    logger.debug(
        f"User {current_user.email} querying planning_OrdresTravails: query={query}, sort={sort}, skip={skip}, limit={limit}"
    )

    service = PlanningOrdresTravailService(db)
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
        logger.debug(f"Found {result['total']} planning_OrdresTravails")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error querying planning_OrdresTravails: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=PlanningOrdresTravailListResponse, responses={400: {"description": "Invalid query JSON format"}, 500: {"description": "Internal Server Error"}})
async def query_planning_OrdresTravails_all(
    *, query: Annotated[str, Query(description="Query conditions (JSON string)")] = None,
    sort: Annotated[str, Query(description="Sort field (prefix with '-' for descending)")] = None,
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(
        ge=1, le=2000, description="Max number of records to return"
    )] = 20,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    logger.debug(
        f"User {current_user.email} querying all planning_OrdresTravails: query={query}, sort={sort}, skip={skip}, limit={limit}"
    )

    service = PlanningOrdresTravailService(db)
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
        logger.debug(f"Found {result['total']} planning_OrdresTravails")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error querying planning_OrdresTravails: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=PlanningOrdresTravailResponse, responses={404: {"description": "PlanningOrdresTravail not found"}, 500: {"description": "Internal Server Error"}})
async def get_planning_OrdresTravail(
    *, id: int,
    fields: Annotated[str, Query(description="Comma-separated list of fields to return")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    logger.debug(f"Fetching planning_OrdresTravail with id: {id}, fields={fields}")

    service = PlanningOrdresTravailService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"PlanningOrdresTravail with id {id} not found")
            raise HTTPException(
                status_code=404, detail=_NOT_FOUND_MSG
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error fetching planning_OrdresTravail {id}: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=PlanningOrdresTravailResponse, status_code=201, responses={400: {"description": "Failed to create planning_OrdresTravail"}, 403: {"description": "You don't have permission to link work orders to this planning"}, 404: {"description": "Planning not found"}, 500: {"description": "Internal Server Error"}})
async def create_planning_OrdresTravail(
    data: PlanningOrdresTravailData,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    logger.debug(f"Creating new planning_OrdresTravail with data: {data}")

    if current_user.role != UserRole.ADMIN:
        planning_query = select(Plannings).where(Plannings.id == data.planning_id)
        planning_result = await db.execute(planning_query)
        planning = planning_result.scalar_one_or_none()

        if not planning:
            raise HTTPException(status_code=404, detail="Planning not found")

        has_access = False
        if current_user.role == UserRole.CHETOP:
            has_access = planning.chef_operation_id == current_user.id
        elif current_user.role == UserRole.CHEFTECH:
            has_access = planning.chef_technique_id == current_user.id

        if not has_access:
            assignment_query = select(PlanningUtilisateurs).where(
                PlanningUtilisateurs.planning_id == data.planning_id,
                PlanningUtilisateurs.utilisateur_id == current_user.id,
            )
            assignment_result = await db.execute(assignment_query)
            assignment = assignment_result.scalar_one_or_none()
            has_access = assignment is not None

        if not has_access:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to link work orders to this planning",
            )

    service = PlanningOrdresTravailService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(
                status_code=400, detail="Failed to create planning_OrdresTravail"
            )

        safe_id = str(result.id).replace("\r", "").replace("\n", "")
        logger.info(f"PlanningOrdresTravail created successfully with id: {safe_id}")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.exception(f"Validation error creating planning_OrdresTravail: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(
            f"Error creating planning_OrdresTravail: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/batch", response_model=list[PlanningOrdresTravailResponse], status_code=201, 
responses={500: {"description": "Internal Server Error"}})
async def create_planning_OrdresTravails_batch(
    request: PlanningOrdresTravailBatchCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    logger.debug(f"Batch creating {len(request.items)} planning_OrdresTravails")

    service = PlanningOrdresTravailService(db)
    results = []

    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)

        logger.info(
            f"Batch created {len(results)} planning_OrdresTravails successfully"
        )
        return results
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=list[PlanningOrdresTravailResponse], responses={500: {"description": "Internal Server Error"}})
async def update_planning_OrdresTravails_batch(
    request: PlanningOrdresTravailBatchUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    logger.debug(f"Batch updating {len(request.items)} planning_OrdresTravails")

    service = PlanningOrdresTravailService(db)
    results = []

    try:
        for item in request.items:
            update_dict = {
                k: v for k, v in item.updates.model_dump().items() if v is not None
            }
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)

        logger.info(
            f"Batch updated {len(results)} planning_OrdresTravails successfully"
        )
        return results
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=PlanningOrdresTravailResponse, responses={400: {"description": "Bad Request"}, 404: {"description": "PlanningOrdresTravail not found"}, 500: {"description": "Internal Server Error"}})
async def update_planning_OrdresTravail(
    id: int,
    data: PlanningOrdresTravailUpdateData,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    logger.debug(f"Updating planning_OrdresTravail {id} with data: {data}")

    service = PlanningOrdresTravailService(db)
    try:
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"PlanningOrdresTravail with id {id} not found for update")
            raise HTTPException(
                status_code=404, detail=_NOT_FOUND_MSG
            )

        logger.info(f"PlanningOrdresTravail {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.exception(
            f"Validation error updating planning_OrdresTravail {id}: {str(e)}"
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(
            f"Error updating planning_OrdresTravail {id}: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch", responses={500: {"description": "Internal Server Error"}})
async def delete_planning_OrdresTravails_batch(
    request: PlanningOrdresTravailBatchDeleteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    logger.debug(f"Batch deleting {len(request.ids)} planning_OrdresTravails")

    service = PlanningOrdresTravailService(db)
    deleted_count = 0

    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1

        logger.info(
            f"Batch deleted {deleted_count} planning_OrdresTravails successfully"
        )
        return {
            "message": f"Successfully deleted {deleted_count} planning_OrdresTravails",
            "deleted_count": deleted_count,
        }
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}", responses={404: {"description": "PlanningOrdresTravail not found"}, 500: {"description": "Internal Server Error"}})
async def delete_planning_OrdresTravail(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    logger.debug(f"Deleting planning_OrdresTravail with id: {id}")

    service = PlanningOrdresTravailService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(
                f"PlanningOrdresTravail with id {id} not found for deletion"
            )
            raise HTTPException(
                status_code=404, detail=_NOT_FOUND_MSG
            )

        logger.info(f"PlanningOrdresTravail {id} deleted successfully")
        return {"message": "PlanningOrdresTravail deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error deleting planning_OrdresTravail {id}: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
