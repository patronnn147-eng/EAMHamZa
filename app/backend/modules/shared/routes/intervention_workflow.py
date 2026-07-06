"""
Phase 2: Intervention → Work Order Workflow

API endpoints for creating interventions from plannings,
validation workflow, and work order generation.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from schemas.pagination import PaginatedResponse
from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs, UserRole
from models.ordres_intervention import Ordres_intervention
from models.ordres_travail import Ordres_travail, OrdreStatut
from models.plannings import Plannings
from models.machines import Machines
from services.audit import AuditService, AuditEntityType
from services.ml.recovery import PostMaintenanceRecoveryService
from .ordres_intervention.schemas import (
    Ordres_interventionResponse,
    Ordres_interventionValidationData,
)
from .ordres_travail.schemas import Ordres_travailResponse

logger = logging.getLogger(__name__)

# Intervention status states for Phase 2 workflow
# PENDING → needs validation by CHEFTECH/ADMIN
# APPROVED → validated, can create work order
# REJECTED → rejected, cannot create work order
# CONVERTED_TO_WORKORDER → work order has been created

router = APIRouter(
    prefix="/api/v1/entities/intervention-workflow", tags=["intervention-workflow"]
)


@router.post(
    "/create",
    response_model=Ordres_interventionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_intervention_from_planning(
    *, planning_id: Annotated[int, Query(description="Planning ID to link intervention to")],
    machine_id: Annotated[int, Query(description="Machine ID")],
    problem_description: Annotated[str, Query(description="Description of the issue")],
    priority: Annotated[str, Query(description="Priority: HAUTE, MOYENNE, BASSE")] = "MOYENNE",
    estimated_duration_minutes: Annotated[Optional[int], Query(
        description="Estimated duration in minutes"
    )] = None,
    required_materials: Annotated[Optional[str], Query(description="Required materials")] = None,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create intervention from a planning.

    Roles that can create: ADMIN, CHEFTECH, CHETOP, TECHNICIAN
    The intervention is created in PENDING status and needs validation.
    """
    # Verify planning exists
    planning = await db.scalar(select(Plannings).where(Plannings.id == planning_id))
    if not planning:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Planning not found"
        )

    # Verify planning is APPROVED (only approved plannings can generate interventions)
    if planning.planning_statut != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot create intervention from planning with status {planning.planning_statut}. Planning must be APPROVED.",
        )

    # Verify machine exists
    machine = await db.scalar(select(Machines).where(Machines.id == machine_id))
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found"
        )

    # Check user permissions
    user_role = current_user.role
    has_permission = False

    if user_role == UserRole.ADMIN:
        has_permission = True
    elif user_role == UserRole.CHEFTECH:
        has_permission = planning.chef_technique_id == current_user.id
    elif user_role == UserRole.CHEFOP:
        has_permission = planning.chef_operation_id == current_user.id
    else:
        # Check if technician is assigned to planning
        from models.planning_utilisateurs import Planning_utilisateurs

        assignment = await db.scalar(
            select(Planning_utilisateurs).where(
                and_(
                    Planning_utilisateurs.planning_id == planning_id,
                    Planning_utilisateurs.utilisateur_id == current_user.id,
                )
            )
        )
        has_permission = assignment is not None

    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to create interventions for this planning",
        )

    now = datetime.now(timezone.utc)

    # Create the intervention
    intervention = Ordres_intervention(
        date_intervention=now,
        planning_id=planning_id,
        machine_id=machine_id,
        problem_description=problem_description,
        priority=priority,
        estimated_duration_minutes=estimated_duration_minutes,
        required_materials=required_materials,
        technician_id=current_user.id,
        requested_by=current_user.id,
        requested_at=now,
        statut="PENDING",  # Phase 2 workflow status
    )

    db.add(intervention)
    await db.commit()
    await db.refresh(intervention)

    # Log audit event
    try:
        await AuditService(db).log_create(
            entity_type=AuditEntityType.INTERVENTION,
            entity_id=intervention.id,
            user_id=current_user.id,
            user_name=current_user.nom,
            new_values={
                "planning_id": planning_id,
                "machine_id": machine_id,
                "problem_description": problem_description,
                "priority": priority,
            },
        )
    except Exception:
        logger.warning("Audit log failed for create intervention %s", intervention.id)

    # nosemgrep: python.fastapi.log.tainted-log-injection-stdlib-fastapi -- all three
    # interpolated values are ints (model PK, FastAPI path/query int params), which
    # cannot carry newline/control-char sequences.
    logger.info(
        "Intervention #%s created from planning #%s by user %s",
        intervention.id,
        planning_id,
        current_user.id,
    )
    return intervention


@router.get("", response_model=PaginatedResponse[Ordres_interventionResponse])
async def list_interventions(
    *, page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 10,
    planning_id: Annotated[Optional[int], Query(description="Filter by planning ID")] = None,
    statut: Annotated[Optional[str], Query(description="Filter by status")] = None,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List interventions with optional filtering."""
    skip = (page - 1) * size

    # Build query based on user role
    if current_user.role == UserRole.ADMIN:
        # Admin sees all
        query = select(Ordres_intervention)
    elif current_user.role == UserRole.CHEFTECH:
        # ChefTech sees their own and pending
        query = select(Ordres_intervention).where(
            or_(
                Ordres_intervention.requested_by == current_user.id,
                Ordres_intervention.statut == "PENDING",
            )
        )
    else:
        # Other users see only their own
        query = select(Ordres_intervention).where(
            Ordres_intervention.requested_by == current_user.id
        )

    # Apply filters
    if planning_id:
        query = query.where(Ordres_intervention.planning_id == planning_id)
    if statut:
        query = query.where(Ordres_intervention.statut == statut)

    # Count total
    count_query = query.with_only_columns(func.count(Ordres_intervention.id))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply ordering and pagination
    query = query.options(
        selectinload(Ordres_intervention.machine),
    )
    query = (
        query.order_by(Ordres_intervention.date_intervention.desc())
        .offset(skip)
        .limit(size)
    )

    # nosemgrep: python.fastapi.db.generic-sql-fastapi -- `query` is a SQLAlchemy
    # Core select() built from ORM column comparisons/joins above (planning_id/statut
    # bound via ==); no raw SQL or string interpolation is involved.
    result = await db.execute(query)
    items = list(result.scalars().all())

    return PaginatedResponse.create(items=items, total=total, page=page, size=size)


@router.get("/{intervention_id}", response_model=Ordres_interventionResponse)
async def get_intervention(
    intervention_id: int,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get intervention by ID."""
    intervention = await db.scalar(
        select(Ordres_intervention).where(Ordres_intervention.id == intervention_id)
    )
    if not intervention:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Intervention not found"
        )
    return intervention


@router.post("/{intervention_id}/validate", response_model=Ordres_interventionResponse)
async def validate_intervention(
    intervention_id: int,
    data: Ordres_interventionValidationData,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Validate or reject an intervention.

    Roles: CHEFTECH, ADMIN only
    Action: "APPROVE" or "REJECT"
    """
    # Check role - only CHEFTECH and ADMIN can validate
    if current_user.role not in [UserRole.CHEFTECH, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only CHEFTECH or ADMIN can validate interventions",
        )

    intervention = await db.scalar(
        select(Ordres_intervention).where(Ordres_intervention.id == intervention_id)
    )
    if not intervention:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Intervention not found"
        )

    # Can only validate PENDING interventions
    if intervention.statut != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot validate intervention with status {intervention.statut}. Only PENDING interventions can be validated.",
        )

    now = datetime.now(timezone.utc)
    old_status = intervention.statut

    if data.action == "APPROVE":
        intervention.statut = "APPROVED"
        intervention.approved_by = current_user.id
        intervention.approved_at = now
    elif data.action == "REJECT":
        intervention.statut = "REJECTED"
        intervention.approved_by = current_user.id
        intervention.approved_at = now
        intervention.rejection_reason = data.rejection_reason
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Use 'APPROVE' or 'REJECT'.",
        )

    await db.commit()
    await db.refresh(intervention)

    # Log audit event
    try:
        await AuditService(db).log_update(
            entity_type=AuditEntityType.INTERVENTION,
            entity_id=intervention_id,
            old_values={"statut": old_status},
            new_values={"statut": intervention.statut, "action": data.action},
            user_id=current_user.id,
            user_name=current_user.nom,
        )
    except Exception:
        logger.warning("Audit log failed for validate intervention %s", intervention_id)

    # nosemgrep: python.fastapi.log.tainted-log-injection-stdlib-fastapi -- by this
    # point data.action is guaranteed to be exactly "APPROVE" or "REJECT" (any other
    # value already raised HTTP 400 above); intervention_id/current_user.id are ints.
    logger.info(
        "Intervention #%s %sed by user %s",
        intervention_id,
        data.action,
        current_user.id,
    )
    return intervention


@router.post(
    "/{intervention_id}/create-work-order", response_model=Ordres_travailResponse
)
async def create_work_order_from_intervention(
    *, intervention_id: int,
    technician_id: Annotated[Optional[int], Query(
        description="Technician to assign the work order to"
    )] = None,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a work order from an approved intervention.

    Roles: CHEFTECH, ADMIN only
    The intervention must be in APPROVED status.
    """
    # Check role - only CHEFTECH and ADMIN can create work orders
    if current_user.role not in [UserRole.CHEFTECH, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only CHEFTECH or ADMIN can create work orders from interventions",
        )

    intervention = await db.scalar(
        select(Ordres_intervention).where(Ordres_intervention.id == intervention_id)
    )
    if not intervention:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Intervention not found"
        )

    # Check status - must be APPROVED
    if intervention.statut != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot create work order from intervention with status {intervention.statut}. Intervention must be APPROVED.",
        )

    # Check if work order already exists
    if intervention.ordre_travail_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Work order already created for this intervention (Work Order #{intervention.ordre_travail_id})",
        )

    now = datetime.now(timezone.utc)

    # Determine technician to assign
    assigned_tech_id = technician_id or intervention.technician_id or current_user.id

    # Create work order linked to intervention
    # Map Phase 2 status to work order status
    wo_statut = OrdreStatut.ASSIGNED

    work_order = Ordres_travail(
        titre=f"[Intervention #{intervention_id}] {intervention.problem_description[:50] if intervention.problem_description else 'Work Order'}",
        description=intervention.problem_description
        or f"Generated from intervention #{intervention_id}",
        priorite=intervention.priority or "MOYENNE",
        statut=wo_statut.value,
        machine_id=intervention.machine_id,
        utilisateur_id=assigned_tech_id,
        created_by=current_user.id,
        validated_by=current_user.id,
        date_validation=now,
    )

    db.add(work_order)
    await db.flush()

    # Update intervention with work order reference
    intervention.ordre_travail_id = work_order.id
    intervention.statut = "CONVERTED_TO_WORKORDER"

    # Post-maintenance recovery: capture pre-maintenance baseline.
    try:
        _score = await PostMaintenanceRecoveryService(db).snapshot_health(
            work_order.machine_id
        )
        if _score is not None:
            work_order.health_score_at_creation = _score
    except Exception as _rec_exc:
        logger.warning(
            "Recovery baseline snapshot failed for WO %s: %s",
            work_order.id,
            _rec_exc,
        )

    await db.commit()
    await db.refresh(work_order)

    # Log audit event
    try:
        await AuditService(db).log_create(
            entity_type=AuditEntityType.WORK_ORDER,
            entity_id=work_order.id,
            user_id=current_user.id,
            user_name=current_user.nom,
            new_values={
                "intervention_id": intervention_id,
                "titre": work_order.titre,
                "machine_id": work_order.machine_id,
            },
        )
    except Exception:
        logger.warning(
            "Audit log failed for create work order from intervention %s",
            intervention_id,
        )

    # nosemgrep: python.fastapi.log.tainted-log-injection-stdlib-fastapi -- all three
    # interpolated values are ints (model PK, FastAPI path param, current user id),
    # which cannot carry newline/control-char sequences.
    logger.info(
        "Work Order #%s created from Intervention #%s by user %s",
        work_order.id,
        intervention_id,
        current_user.id,
    )
    return work_order


@router.get("/pending", response_model=List[Ordres_interventionResponse])
async def get_pending_interventions(
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get all interventions pending validation.

    Roles: CHEFTECH, ADMIN only
    """
    if current_user.role not in [UserRole.CHEFTECH, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only CHEFTECH or ADMIN can view pending interventions",
        )

    result = await db.execute(
        select(Ordres_intervention)
        .where(Ordres_intervention.statut == "PENDING")
        .order_by(Ordres_intervention.date_intervention.desc())
    )
    items = list(result.scalars().all())
    return items
