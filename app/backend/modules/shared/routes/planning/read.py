import logging
from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from schemas.pagination import PaginatedResponse
from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs, UserRole
from models.plannings import Plannings
from models.planning_machines import PlanningMachines
from models.planning_utilisateurs import PlanningUtilisateurs
from models.planning_taches import PlanningTaches
from models.machines import Machines
from services.plannings import PlanningsService
from .schemas import PlanningResponse, PlanningMachineResponse, UserOption
from .helpers import get_planning_with_users

router = APIRouter(prefix="/api/v1/plannings", tags=["plannings"])
logger = logging.getLogger(__name__)


@router.get("", response_model=PaginatedResponse[PlanningResponse])
async def list_plannings(
    *, page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 10,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List plannings filtered by user role and assignments"""
    skip = (page - 1) * size
    limit = size
    try:
        service = PlanningsService(db)

        # Admin can see all plannings
        if current_user.role == UserRole.ADMIN:
            result = await service.get_list(skip=skip, limit=limit, sort="-date_debut")
        else:
            # Non-admin users can only see their assigned plannings
            # Role-specific filtering for more precision
            if current_user.role == UserRole.CHETOP:
                # Chef Opérateur sees plannings where they are responsible
                query = select(Plannings.id).where(
                    Plannings.chef_operation_id == current_user.id
                )
            elif current_user.role == UserRole.CHEFTECH:
                # Chef Technique sees plannings where they are responsible
                query = select(Plannings.id).where(
                    Plannings.chef_technique_id == current_user.id
                )
            else:
                # Technicians see plannings where they are explicitly assigned in PlanningUtilisateurs
                query = select(PlanningUtilisateurs.planning_id).where(
                    PlanningUtilisateurs.utilisateur_id == current_user.id
                )

            planning_ids_result = await db.execute(query.distinct())
            planning_ids = [row[0] for row in planning_ids_result.fetchall()]

            if not planning_ids:
                # User has no assigned plannings
                return PaginatedResponse.create(items=[], total=0, page=page, size=size)

            # Get only the plannings where user is assigned
            data_query = (
                select(Plannings)
                .where(Plannings.id.in_(planning_ids))
                .where(Plannings.archived_at.is_(None))
            )

            # Eager load relationships to avoid N+1 in get_planning_with_users
            data_query = data_query.options(
                selectinload(Plannings.PlanningUtilisateurs).selectinload(
                    PlanningUtilisateurs.utilisateur
                ),
                selectinload(Plannings.PlanningMachines),
            )

            # Apply sorting
            data_query = data_query.order_by(Plannings.date_debut.desc())

            # Apply pagination
            data_query = data_query.offset(skip).limit(limit)

            # nosemgrep: python.fastapi.db.generic-sql-fastapi -- `data_query` is a
            # SQLAlchemy Core select() filtered via .in_()/.is_() on ORM columns;
            # no raw SQL or string interpolation is involved.
            # Execute query
            plannings_result = await db.execute(data_query)
            plannings_objs = plannings_result.scalars().all()

            # Get total count
            count_query = (
                select(func.count(Plannings.id))
                .where(Plannings.id.in_(planning_ids))
                .where(Plannings.archived_at.is_(None))
            )
            count_result = await db.execute(count_query)
            total = count_result.scalar() or 0

            items = []
            for p in plannings_objs:
                items.append(await get_planning_with_users(db, p))

            return PaginatedResponse.create(
                items=items, total=total, page=page, size=size
            )

        # Enrich with assigned users
        items_with_users = []
        for planning in result["items"]:
            planning_dict = await get_planning_with_users(db, planning)
            items_with_users.append(PlanningResponse(**planning_dict))

        return PaginatedResponse.create(
            items=items_with_users, total=result["total"], page=page, size=size
        )
    except Exception as e:
        logger.exception(f"Error listing plannings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list plannings: {str(e)}",
        )


@router.get("/all-with-taches", response_model=list[dict])
async def list_plannings_with_tasks(
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List all plannings with their task counts"""
    try:
        tasks_subquery = (
            select(
                PlanningTaches.planning_id,
                func.count(PlanningTaches.id).label("task_count"),
            )
            .where(PlanningTaches.archived_at.is_(None))
            .group_by(PlanningTaches.planning_id)
            .subquery()
        )

        result = await db.execute(
            select(
                Plannings.id,
                Plannings.identifiant_planning,
                Plannings.date_debut,
                Plannings.date_fin,
                Plannings.planning_statut,
                func.coalesce(tasks_subquery.c.task_count, 0).label("task_count"),
            )
            .outerjoin(tasks_subquery, Plannings.id == tasks_subquery.c.planning_id)
            .where(Plannings.archived_at.is_(None))
            .order_by(Plannings.date_debut.desc())
        )
        rows = result.all()

        return [
            {
                "id": row[0],
                "identifiant_planning": row[1],
                "date_debut": row[2],
                "date_fin": row[3],
                "planning_statut": row[4],
                "task_count": row[5],
            }
            for row in rows
        ]
    except Exception as e:
        logger.exception(f"Error listing plannings with tasks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list plannings: {str(e)}",
        )


@router.get("/{planning_id}", response_model=PlanningResponse)
async def get_planning(
    planning_id: int,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get planning details with role-based access control"""
    try:
        service = PlanningsService(db)
        planning = await service.get_by_id(planning_id)

        if not planning:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Planning not found"
            )

        # Check if user has access to this planning
        if current_user.role != UserRole.ADMIN:
            has_access = False
            if current_user.role == UserRole.CHETOP:
                has_access = planning.chef_operation_id == current_user.id
            elif current_user.role == UserRole.CHEFTECH:
                has_access = planning.chef_technique_id == current_user.id

            # If not already found as chef, check the bridge table (especially for technicians)
            if not has_access:
                pu_result = await db.execute(
                    select(PlanningUtilisateurs).where(
                        PlanningUtilisateurs.planning_id == planning_id,
                        PlanningUtilisateurs.utilisateur_id == current_user.id,
                    )
                )
                has_access = pu_result.scalar_one_or_none() is not None

            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have access to this planning",
                )

        planning_dict = await get_planning_with_users(db, planning)
        return PlanningResponse(**planning_dict)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching planning {planning_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch planning: {str(e)}",
        )


@router.get("/{planning_id}/machines", response_model=List[PlanningMachineResponse])
async def get_PlanningMachines(
    planning_id: int,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get machines assigned to a planning with role-based access control"""
    try:
        service = PlanningsService(db)
        planning = await service.get_by_id(planning_id)

        if not planning:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Planning not found",
            )

        if current_user.role != UserRole.ADMIN:
            # Check if user is responsible for this planning
            has_access = False
            if current_user.role == UserRole.CHETOP:
                has_access = planning.chef_operation_id == current_user.id
            elif current_user.role == UserRole.CHEFTECH:
                has_access = planning.chef_technique_id == current_user.id

            # If not responsible, check if explicitly assigned (bridge table)
            if not has_access:
                assignment_query = select(PlanningUtilisateurs).where(
                    PlanningUtilisateurs.planning_id == planning_id,
                    PlanningUtilisateurs.utilisateur_id == current_user.id,
                )
                assignment_result = await db.execute(assignment_query)
                assignment = assignment_result.scalar_one_or_none()
                has_access = assignment is not None

            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to view machines for this planning",
                )

        result = await db.execute(
            select(Machines)
            .join(PlanningMachines, PlanningMachines.machine_id == Machines.id)
            .where(PlanningMachines.planning_id == planning_id)
            .order_by(Machines.nom.asc())
        )
        machines = result.scalars().all()
        return [PlanningMachineResponse.model_validate(m) for m in machines]
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error fetching planning machines for {planning_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch planning machines: {str(e)}",
        )


@router.get("/{planning_id}/users", response_model=List[UserOption])
async def get_planning_users(
    planning_id: int,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get users assigned to a planning"""
    try:
        result = await db.execute(
            select(Utilisateurs)
            .join(
                PlanningUtilisateurs,
                PlanningUtilisateurs.utilisateur_id == Utilisateurs.id,
            )
            .where(PlanningUtilisateurs.planning_id == planning_id)
        )
        users = result.scalars().all()

        return [
            UserOption(
                id=user.id,
                nom=user.nom,
                email=user.email,
                role=user.role.value,
                shift_type=user.shift_type.value
                if hasattr(user.shift_type, "value")
                else str(user.shift_type),
            )
            for user in users
        ]
    except Exception as e:
        logger.exception(f"Error fetching planning users for {planning_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch planning users: {str(e)}",
        )
