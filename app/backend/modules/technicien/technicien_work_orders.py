from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from schemas.pagination import PaginatedResponse
from datetime import datetime
import logging
from pydantic import BaseModel

from core.database import get_db
from core.security import verify_technicien
from models.utilisateurs import Utilisateurs, UserRole
from models.machines import Machines
from models.ordres_travail import Ordres_travail, OrdreStatut
from models.ordres_intervention import Ordres_intervention
from models.planning_taches import Planning_taches
from models.machine_telemetry import MachineTelemetry
from services.audit import AuditService, AuditEntityType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/technicien", tags=["technicien"])

class WorkOrderResponse(BaseModel):
    id: int
    titre: str
    description: Optional[str] = None
    priorite: str
    statut: str
    machine_id: int
    machine_nom: Optional[str] = None
    created_at: datetime

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
    
    # Machine Telemetry fields (all optional)
    air_temperature: Optional[float] = None
    process_temperature: Optional[float] = None
    rotational_speed: Optional[int] = None
    torque: Optional[float] = None
    tool_wear: Optional[int] = None
    telemetry_notes: Optional[str] = None


@router.get("/work-orders", response_model=PaginatedResponse[WorkOrderResponse])
async def get_my_work_orders(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    current_user: Utilisateurs = Depends(verify_technicien),
    db: AsyncSession = Depends(get_db),
):
    """TECHNICIEN: List work orders assigned to this technician"""
    try:
        skip = (page - 1) * size

        # Count total - also check Ordres_travail.utilisateur_id directly
        count_query = select(func.count(Ordres_travail.id))\
            .outerjoin(Ordres_intervention, Ordres_travail.id == Ordres_intervention.ordre_travail_id)\
            .where(
                (Ordres_intervention.technician_id == current_user.id) |
                (Ordres_travail.utilisateur_id == current_user.id)
            )
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = select(Ordres_travail, Machines.nom.label("machine_nom"))\
            .outerjoin(Ordres_intervention, Ordres_travail.id == Ordres_intervention.ordre_travail_id)\
            .outerjoin(Machines, Ordres_travail.machine_id == Machines.id)\
            .where(
                (Ordres_intervention.technician_id == current_user.id) |
                (Ordres_travail.utilisateur_id == current_user.id)
            )\
            .order_by(Ordres_travail.created_at.desc()).offset(skip).limit(size)
        
        result = await db.execute(query)
        rows = result.all()
        
        items = [
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
        logger.error(f"Error fetching work orders for technician: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.patch("/work-orders/{order_id}/start")
async def start_work_order(
    order_id: int,
    current_user: Utilisateurs = Depends(verify_technicien),
    db: AsyncSession = Depends(get_db),
):
    """TECHNICIEN: Start an assigned work order"""
    try:
        # Check if work order exists and belongs to this technician
        wo_result = await db.execute(
            select(Ordres_travail).where(Ordres_travail.id == order_id)
        )
        wo = wo_result.scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="Work order not found")
        
        # Allow if either utilisateur_id matches OR intervention link exists
        has_access = False
        if wo.utilisateur_id == current_user.id:
            has_access = True
        else:
            # Check via intervention link
            int_result = await db.execute(
                select(Ordres_intervention).where(
                    Ordres_intervention.ordre_travail_id == order_id,
                    Ordres_intervention.technician_id == current_user.id
                )
            )
            if int_result.scalar_one_or_none():
                has_access = True
        
        if not has_access:
            raise HTTPException(status_code=403, detail="You can only start work orders assigned to you")
        
        if wo.statut not in ["EN_ATTENTE", "ASSIGNÉ", "ASSIGNED"]:
            raise HTTPException(status_code=400, detail="Only pending/assigned orders can be started")

        previous_statut = wo.statut
        now = datetime.utcnow()
        wo.statut = OrdreStatut.IN_PROGRESS
        if not wo.date_debut:
            wo.date_debut = now
        
        # Update linked intervention if exists
        int_result = await db.execute(
            select(Ordres_intervention).where(
                Ordres_intervention.ordre_travail_id == order_id
            )
        )
        intervention = int_result.scalar_one_or_none()
        if intervention:
            intervention.statut = "EN_COURS"
            if not intervention.date_debut:
                intervention.date_debut = now
            
        await db.commit()

        try:
            await AuditService(db).log_update(
                entity_type=AuditEntityType.WORK_ORDER,
                entity_id=order_id,
                old_values={"statut": previous_statut},
                new_values={"statut": OrdreStatut.IN_PROGRESS},
                user_id=current_user.id,
                user_name=current_user.nom,
                entity_name=wo.titre,
            )
        except Exception:
            logger.warning("Audit log failed for technician start work order %s", order_id)

        return {"message": "Work order started", "statut": OrdreStatut.IN_PROGRESS}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error starting work order: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.patch("/work-orders/{order_id}/complete")
async def complete_work_order(
    order_id: int,
    payload: WorkOrderCompletePayload,
    current_user: Utilisateurs = Depends(verify_technicien),
    db: AsyncSession = Depends(get_db),
):
    """TECHNICIEN: Complete a work order with full PDCA data"""
    try:
        # Check if work order exists
        wo_result = await db.execute(select(Ordres_travail).where(Ordres_travail.id == order_id))
        wo = wo_result.scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="Work order not found")
        
        # Allow if either utilisateur_id matches OR intervention link exists
        has_access = False
        if wo.utilisateur_id == current_user.id:
            has_access = True
        else:
            int_result = await db.execute(
                select(Ordres_intervention).where(
                    Ordres_intervention.ordre_travail_id == order_id,
                    Ordres_intervention.technician_id == current_user.id
                )
            )
            if int_result.scalar_one_or_none():
                has_access = True
        
        if not has_access:
            raise HTTPException(status_code=403, detail="You can only complete work orders assigned to you")
        
        if wo.statut != OrdreStatut.IN_PROGRESS:
            raise HTTPException(status_code=400, detail="Only 'IN_PROGRESS' orders can be completed")

        now = datetime.utcnow()
        wo.statut = OrdreStatut.COMPLETED
        wo.date_fin = now
        wo.rapport = payload.rapport
        
        # Update linked intervention if exists
        int_result = await db.execute(
            select(Ordres_intervention).where(
                Ordres_intervention.ordre_travail_id == order_id
            )
        )
        intervention = int_result.scalar_one_or_none()
        if intervention:
            intervention.statut = "TERMINÉ"
            intervention.rapport = payload.rapport
            if not intervention.date_debut:
                intervention.date_debut = wo.date_debut or now
            intervention.date_fin = now
            
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

            if intervention.planning_tache_id:
                tache = await db.scalar(
                    select(Planning_taches).where(Planning_taches.id == intervention.planning_tache_id)
                )
                if tache:
                    tache.statut = "COMPLETED"

        # Save telemetry if any telemetry field is provided
        if any([
            payload.air_temperature,
            payload.process_temperature,
            payload.rotational_speed,
            payload.torque,
            payload.tool_wear,
        ]):
            telemetry = MachineTelemetry(
                machine_id=wo.machine_id,
                work_order_id=wo.id,
                technician_id=current_user.id,
                air_temperature=payload.air_temperature or 0,
                process_temperature=payload.process_temperature or 0,
                rotational_speed=payload.rotational_speed or 0,
                torque=payload.torque or 0,
                tool_wear=payload.tool_wear or 0,
                recorded_at=now,
                notes=payload.telemetry_notes,
            )
            db.add(telemetry)
        
        await db.commit()

        try:
            await AuditService(db).log_update(
                entity_type=AuditEntityType.WORK_ORDER,
                entity_id=order_id,
                old_values={"statut": "EN_COURS"},
                new_values={"statut": "TERMINÉ", "rapport": payload.rapport},
                user_id=current_user.id,
                user_name=current_user.nom,
                entity_name=wo.titre,
            )
        except Exception:
            logger.warning("Audit log failed for technician complete work order %s", order_id)

        return {"message": "Work order completed via PDCA form", "statut": "TERMINÉ"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error completing work order: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
