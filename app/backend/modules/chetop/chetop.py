"""
CHETOP (Chef des Opérations) Routes - Based on User Stories
"""
import json
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from schemas.pagination import PaginatedResponse

from core.database import get_db
from core.auth import get_current_user
from core.rabbitmq import (
    get_rabbitmq,
    ROUTING_KEY_WO_CREATED,
    ROUTING_KEY_WO_STATUS_CHANGED,
)
from models.utilisateurs import Utilisateurs, UserRole
from models.ordres_travail import Ordres_travail
from models.machines import Machines
from models.ordres_intervention import Ordres_intervention
from tasks.work_order_events import (
    notify_work_order_status_changed,
)

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chetop", tags=["chetop"])


class InterventionRequestCreate(BaseModel):
    """ChefOp requests an intervention (PDS) - Enhanced"""
    machine_id: int
    priorite: str = "MOYENNE"
    description: str
    
    # Enhanced DI fields
    machine_category: Optional[str] = None
    symptoms: Optional[str] = None
    problem_start_time: Optional[datetime] = None
    frequency: Optional[str] = None
    operating_state: Optional[str] = None
    load_level: Optional[int] = None
    temperature: Optional[str] = None
    impact: Optional[str] = None
    estimated_loss: Optional[str] = None
    similar_issue_before: Optional[bool] = None
    
    # AI placeholders (usually filled by backend/ML service)
    suggested_cause: Optional[str] = None
    suggested_priority: Optional[str] = None
    risk_score: Optional[str] = None

class WorkOrderResponse(BaseModel):
    id: int
    titre: str
    description: Optional[str] = None
    priorite: str
    statut: str
    machine_id: int
    machine_nom: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class InterventionRequestResponse(BaseModel):
    id: int
    machine_id: int
    machine_nom: Optional[str] = None
    priorite: str
    description: str
    statut: str
    requested_at: Optional[datetime] = None
    ordre_travail_id: Optional[int] = None
    rejection_reason: Optional[str] = None

    class Config:
        from_attributes = True

class MachineStatusUpdate(BaseModel):
    """US-CHETOP-007: Update machine status"""
    statut: str  # disponible, en_maintenance, hors_service
    commentaire: Optional[str] = None


class MachineResponse(BaseModel):
    """US-CHETOP-006: Machine with status"""
    id: int
    nom: str
    emplacement: Optional[str] = None
    type: Optional[str] = None
    statut: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    """CHETOP Dashboard Statistics"""
    total_requests: int
    requests_pending: int
    requests_approved: int
    requests_rejected: int
    total_machines: int
    machines_en_maintenance: int
    machines_hors_service: int


# ---------- Routes ----------
@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """CHETOP Dashboard - Updated for Intervention Requests"""
    try:
        from models.ordres_intervention import Ordres_intervention
        
        # Request statistics
        total_requests_result = await db.execute(
            select(Ordres_intervention)
            .options(selectinload(Ordres_intervention.machine))
        )
        total_requests = len(total_requests_result.scalars().all())
        
        pending_result = await db.execute(
            select(Ordres_intervention).where(Ordres_intervention.statut == "EN_ATTENTE")
        )
        requests_pending = len(pending_result.scalars().all())
        
        approved_result = await db.execute(
            select(Ordres_intervention).where(Ordres_intervention.statut == "ACCEPTED")
        )
        requests_approved = len(approved_result.scalars().all())
        
        rejected_result = await db.execute(
            select(Ordres_intervention).where(Ordres_intervention.statut == "REJECTED")
        )
        requests_rejected = len(rejected_result.scalars().all())
        
        # Machine statistics
        total_machines_result = await db.execute(
            select(Machines)
        )
        total_machines = len(total_machines_result.scalars().all())
        
        machines_en_maintenance_result = await db.execute(
            select(Machines).where(Machines.statut == "en_maintenance")
        )
        machines_en_maintenance = len(machines_en_maintenance_result.scalars().all())
        
        machines_hors_service_result = await db.execute(
            select(Machines).where(Machines.statut == "hors_service")
        )
        machines_hors_service = len(machines_hors_service_result.scalars().all())
        
        return DashboardStats(
            total_requests=total_requests,
            requests_pending=requests_pending,
            requests_approved=requests_approved,
            requests_rejected=requests_rejected,
            total_machines=total_machines,
            machines_en_maintenance=machines_en_maintenance,
            machines_hors_service=machines_hors_service
        )
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/intervention-requests", response_model=InterventionRequestResponse, status_code=201)
async def create_intervention_request(
    data: InterventionRequestCreate,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """ChefOp requests an intervention (PDS)"""
    try:
        from models.ordres_intervention import Ordres_intervention
        
        # Validate machine exists
        machine_result = await db.execute(select(Machines).where(Machines.id == data.machine_id))
        machine = machine_result.scalar_one_or_none()
        if not machine:
            raise HTTPException(status_code=404, detail="Machine not found")
        
        new_request = Ordres_intervention(
            machine_id=data.machine_id,
            priority=data.priorite,
            problem_description=data.description,
            statut="EN_ATTENTE",
            date_intervention=datetime.utcnow(),  # Required NOT NULL field
            requested_at=datetime.utcnow(),
            ordre_travail_id=0, # Temporary placeholder
            technicien_id=current_user.id, # ChefOp who requested
            
            # New enhanced fields
            machine_category=data.machine_category,
            symptoms=data.symptoms,
            problem_start_time=data.problem_start_time,
            frequency=data.frequency,
            operating_state=data.operating_state,
            load_level=data.load_level,
            temperature=data.temperature,
            impact=data.impact,
            estimated_loss=data.estimated_loss,
            similar_issue_before=data.similar_issue_before,
            suggested_cause=data.suggested_cause,
            suggested_priority=data.suggested_priority,
            risk_score=data.risk_score
        )
        
        db.add(new_request)
        await db.commit()
        await db.refresh(new_request)
        
        return InterventionRequestResponse(
            id=new_request.id,
            machine_id=new_request.machine_id,
            machine_nom=machine.nom,
            priorite=new_request.priority or "MOYENNE",
            description=new_request.problem_description or "",
            statut=new_request.statut,
            requested_at=new_request.requested_at
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating request: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/work-orders", response_model=PaginatedResponse[WorkOrderResponse])
async def get_my_work_orders(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """CHETOP: List work orders generated from my intervention requests"""
    if current_user.role != UserRole.CHETOP:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        skip = (page - 1) * size
        
        # Count total
        count_query = select(func.count(Ordres_travail.id))\
            .join(Ordres_intervention, Ordres_travail.id == Ordres_intervention.ordre_travail_id)\
            .where(Ordres_intervention.technicien_id == current_user.id)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Join with Ordres_intervention to find WOs requested by this user
        query = select(Ordres_travail, Machines.nom.label("machine_nom"))\
            .join(Ordres_intervention, Ordres_travail.id == Ordres_intervention.ordre_travail_id)\
            .outerjoin(Machines, Ordres_travail.machine_id == Machines.id)\
            .where(Ordres_intervention.technicien_id == current_user.id)\
            .order_by(Ordres_travail.created_at.desc()).offset(skip).limit(size)
        
        result = await db.execute(query)
        rows = result.all()
        
        return [
            WorkOrderResponse(
                id=wo.id,
                titre=wo.titre,
                description=wo.description,
                priorite=wo.priorite,
                statut=wo.statut,
                machine_id=wo.machine_id,
                machine_nom=machine_nom,
                created_at=wo.created_at
            ) for wo, machine_nom in rows
        ]

        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            size=size
        )
    except Exception as e:
        logger.error(f"Error fetching work orders: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.patch("/work-orders/{order_id}/start")
async def start_work_order(
    order_id: int,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """CHETOP: Start a work order"""
    if current_user.role != UserRole.CHETOP:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        # Verify ownership via intervention request
        check_query = select(Ordres_intervention)\
            .where(Ordres_intervention.ordre_travail_id == order_id)\
            .where(Ordres_intervention.technicien_id == current_user.id)
        
        check_result = await db.execute(check_query)
        if not check_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="You can only start work orders you requested")
            
        wo_result = await db.execute(select(Ordres_travail).where(Ordres_travail.id == order_id))
        wo = wo_result.scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="Work order not found")
        
        if wo.statut != "EN_ATTENTE":
            raise HTTPException(status_code=400, detail="Only 'EN_ATTENTE' orders can be started")
            
        wo.statut = "EN_COURS"
        wo.date_debut = datetime.utcnow()
        await db.commit()
        
        return {"message": "Work order started", "statut": "EN_COURS"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error starting work order: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

class WorkOrderCompletePayload(BaseModel):
    rapport: str
    
    # Enhanced Report fields
    intervention_type: Optional[str] = None
    root_cause_category: Optional[str] = None
    root_cause_description: Optional[str] = None
    actions_performed: Optional[str] = None
    parts_replaced: Optional[str] = None
    tools_used: Optional[str] = None
    machine_status_after: Optional[str] = None
    
    # PDCA Specific
    plan_hypothesis: Optional[str] = None
    check_resolved: Optional[bool] = None
    check_verification_method: Optional[str] = None
    act_preventive_actions: Optional[str] = None
    act_recommendations: Optional[str] = None

@router.patch("/work-orders/{order_id}/complete")
async def complete_work_order(
    order_id: int,
    payload: WorkOrderCompletePayload,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """CHETOP: Complete a work order"""
    if current_user.role != UserRole.CHETOP:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        # Verify ownership via intervention request
        check_query = select(Ordres_intervention)\
            .where(Ordres_intervention.ordre_travail_id == order_id)\
            .where(Ordres_intervention.technicien_id == current_user.id)
        
        check_result = await db.execute(check_query)
        intervention = check_result.scalar_one_or_none()
        if not intervention:
            raise HTTPException(status_code=403, detail="You can only complete work orders you requested")
            
        wo_result = await db.execute(select(Ordres_travail).where(Ordres_travail.id == order_id))
        wo = wo_result.scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="Work order not found")
        
        if wo.statut != "EN_COURS":
            raise HTTPException(status_code=400, detail="Only 'EN_COURS' orders can be completed")
            
        now = datetime.utcnow()
        wo.statut = "TERMINÉ"
        wo.date_fin = now
        wo.rapport = payload.rapport
        
        # Also update the associated intervention with enhanced fields
        intervention.statut = "TERMINÉ"
        intervention.rapport = payload.rapport
        if not intervention.date_debut:
            intervention.date_debut = wo.date_debut or now
        intervention.date_fin = now
        
        # New Report and PDCA fields
        intervention.intervention_type = payload.intervention_type
        intervention.root_cause_category = payload.root_cause_category
        intervention.root_cause_description = payload.root_cause_description
        intervention.actions_performed = payload.actions_performed
        intervention.parts_replaced = payload.parts_replaced
        intervention.tools_used = payload.tools_used
        intervention.machine_status_after = payload.machine_status_after
        
        intervention.plan_hypothesis = payload.plan_hypothesis
        intervention.check_resolved = payload.check_resolved
        intervention.check_verification_method = payload.check_verification_method
        intervention.act_preventive_actions = payload.act_preventive_actions
        intervention.act_recommendations = payload.act_recommendations
        
        # New Report and PDCA fields
        intervention.intervention_type = payload.intervention_type
        intervention.root_cause_category = payload.root_cause_category
        intervention.root_cause_description = payload.root_cause_description
        intervention.actions_performed = payload.actions_performed
        intervention.parts_replaced = payload.parts_replaced
        intervention.tools_used = payload.tools_used
        intervention.machine_status_after = payload.machine_status_after
        
        intervention.plan_hypothesis = payload.plan_hypothesis
        intervention.check_resolved = payload.check_resolved
        intervention.check_verification_method = payload.check_verification_method
        intervention.act_preventive_actions = payload.act_preventive_actions
        intervention.act_recommendations = payload.act_recommendations
        
        await db.commit()
        
        return {"message": "Work order completed", "statut": "TERMINÉ"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error completing work order: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/intervention-requests", response_model=PaginatedResponse[InterventionRequestResponse])
async def get_my_intervention_requests(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List ChefOp's own intervention requests"""
    try:
        from models.ordres_intervention import Ordres_intervention
        
        skip = (page - 1) * size
        
        # Count total
        count_query = select(func.count(Ordres_intervention.id)).where(Ordres_intervention.technicien_id == current_user.id)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = select(Ordres_intervention, Machines.nom.label("machine_nom"))\
            .outerjoin(Machines, Ordres_intervention.machine_id == Machines.id)\
            .where(Ordres_intervention.technicien_id == current_user.id)\
            .order_by(Ordres_intervention.requested_at.desc()).offset(skip).limit(size)
        
        result = await db.execute(query)
        rows = result.all()
        
        return [
            InterventionRequestResponse(
                id=itv.id,
                machine_id=itv.machine_id,
                machine_nom=machine_nom,
                priorite=itv.priority or "MOYENNE",
                description=itv.problem_description or "",
                statut=itv.statut,
                requested_at=itv.requested_at,
                rejection_reason=itv.rejection_reason
            ) for itv, machine_nom in rows
        ]

        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            size=size
        )
    except Exception as e:
        logger.error(f"Error listing requests: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/machines", response_model=PaginatedResponse[MachineResponse])
async def get_machines(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    statut: Optional[str] = Query(None, description="Filter by status"),
    type: Optional[str] = Query(None, description="Filter by type"),
    emplacement: Optional[str] = Query(None, description="Filter by location"),
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-CHETOP-006: Get machines with status overview"""
    try:
        skip = (page - 1) * size
        
        # Count total with filters
        count_query = select(func.count(Machines.id))
        if statut:
            count_query = count_query.where(Machines.statut == statut)
        if type:
            count_query = count_query.where(Machines.type == type)
        if emplacement:
            count_query = count_query.where(Machines.emplacement.ilike(f"%{emplacement}%"))
        
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = select(Machines)
        
        if statut:
            query = query.where(Machines.statut == statut)
        if type:
            query = query.where(Machines.type == type)
        if emplacement:
            query = query.where(Machines.emplacement.ilike(f"%{emplacement}%"))
        
        query = query.order_by(Machines.nom).offset(skip).limit(size)
        
        result = await db.execute(query)
        machines = result.scalars().all()
        
        return [MachineResponse(
            id=machine.id,
            nom=machine.nom,
            emplacement=machine.emplacement,
            type=machine.type,
            statut=machine.statut,
            created_at=machine.created_at
        ) for machine in machines]

        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            size=size
        )
    except Exception as e:
        logger.error(f"Error getting machines: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/machines/{machine_id}/status", response_model=MachineResponse)
async def update_machine_status(
    machine_id: int,
    data: MachineStatusUpdate,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-CHETOP-007: Update machine status"""
    try:
        # Get machine
        machine_result = await db.execute(
            select(Machines).where(Machines.id == machine_id)
        )
        machine = machine_result.scalar_one_or_none()
        if not machine:
            raise HTTPException(status_code=404, detail="Machine not found")
        
        # Update status
        machine.statut = data.statut
        # Note: You might want to add a comment field to the Machines model for tracking status changes
        
        await db.commit()
        await db.refresh(machine)
        
        return MachineResponse(
            id=machine.id,
            nom=machine.nom,
            emplacement=machine.emplacement,
            type=machine.type,
            statut=machine.statut,
            created_at=machine.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating machine status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
