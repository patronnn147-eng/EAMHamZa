from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime
import logging
from pydantic import BaseModel

from core.database import get_db
from core.security import verify_technicien
from models.utilisateurs import Utilisateurs, UserRole
from models.machines import Machines
from models.ordres_travail import Ordres_travail
from models.ordres_intervention import Ordres_intervention

logger = logging.getLogger(__name__)
router = APIRouter()

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


@router.get("/work-orders", response_model=List[WorkOrderResponse])
async def get_my_work_orders(
    current_user: Utilisateurs = Depends(verify_technicien),
    db: AsyncSession = Depends(get_db),
):
    """TECHNICIEN: List work orders assigned to this technician"""
    try:
        query = select(Ordres_travail, Machines.nom.label("machine_nom"))\
            .join(Ordres_intervention, Ordres_travail.id == Ordres_intervention.ordre_travail_id)\
            .outerjoin(Machines, Ordres_travail.machine_id == Machines.id)\
            .where(Ordres_intervention.technicien_id == current_user.id)
        
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
        check_query = select(Ordres_intervention)\
            .where(Ordres_intervention.ordre_travail_id == order_id)\
            .where(Ordres_intervention.technicien_id == current_user.id)
        
        check_result = await db.execute(check_query)
        intervention = check_result.scalar_one_or_none()
        if not intervention:
            raise HTTPException(status_code=403, detail="You can only start work orders assigned to you")
            
        wo_result = await db.execute(select(Ordres_travail).where(Ordres_travail.id == order_id))
        wo = wo_result.scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="Work order not found")
        
        if wo.statut not in ["EN_ATTENTE", "ASSIGNÉ"]:
            raise HTTPException(status_code=400, detail="Only pending/assigned orders can be started")
            
        now = datetime.utcnow()
        wo.statut = "EN_COURS"
        if not wo.date_debut:
            wo.date_debut = now
            
        intervention.statut = "EN_COURS"
        if not intervention.date_debut:
            intervention.date_debut = now
            
        await db.commit()
        
        return {"message": "Work order started", "statut": "EN_COURS"}
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
        check_query = select(Ordres_intervention)\
            .where(Ordres_intervention.ordre_travail_id == order_id)\
            .where(Ordres_intervention.technicien_id == current_user.id)
        
        check_result = await db.execute(check_query)
        intervention = check_result.scalar_one_or_none()
        if not intervention:
            raise HTTPException(status_code=403, detail="You can only complete work orders assigned to you")
            
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
        
        await db.commit()
        
        return {"message": "Work order completed via PDCA form", "statut": "TERMINÉ"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error completing work order: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
