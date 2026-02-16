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
from sqlalchemy import select, and_, or_

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
from tasks.work_order_events import (
    notify_work_order_created,
    notify_work_order_status_changed,
)

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chetop", tags=["chetop"])


# ---------- Pydantic Schemas ----------
class WorkOrderCreate(BaseModel):
    """US-CHETOP-001: Create new work order"""
    titre: str  # Title of work order
    description: str  # Detailed description
    priorite: str = "MOYENNE"  # BASSE, MOYENNE, ÉLEVÉE, URGENTE (US-CHETOP-002)
    machine_id: int  # Associated machine (US-CHETOP-003)
    utilisateur_id: Optional[int] = None  # Assigned user (US-CHETOP-005)
    date_echeance: Optional[datetime] = None  # Due date (US-CHETOP-001)


class WorkOrderUpdate(BaseModel):
    """US-CHETOP-004: Update work order status"""
    statut: str  # EN_ATTENTE, EN_COURS, TERMINÉ, ANNULÉ
    priorite: Optional[str] = None
    utilisateur_id: Optional[int] = None
    date_echeance: Optional[datetime] = None


class WorkOrderResponse(BaseModel):
    """Work order response with related data"""
    id: int
    titre: str
    description: str
    priorite: str
    statut: str
    date_echeance: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    machine_id: int
    machine_nom: Optional[str] = None
    utilisateur_id: Optional[int] = None
    utilisateur_nom: Optional[str] = None

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
    total_ordres: int
    ordres_en_attente: int
    ordres_en_cours: int
    ordres_termines: int
    ordres_urgents: int
    total_machines: int
    machines_en_maintenance: int
    machines_hors_service: int


# ---------- Routes ----------
@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """CHETOP Dashboard - Overview statistics"""
    try:
        # Work order statistics
        total_ordres_result = await db.execute(select(Ordres_travail))
        total_ordres = len(total_ordres_result.scalars().all())
        
        ordres_en_attente_result = await db.execute(
            select(Ordres_travail).where(Ordres_travail.statut == "EN_ATTENTE")
        )
        ordres_en_attente = len(ordres_en_attente_result.scalars().all())
        
        ordres_en_cours_result = await db.execute(
            select(Ordres_travail).where(Ordres_travail.statut == "EN_COURS")
        )
        ordres_en_cours = len(ordres_en_cours_result.scalars().all())
        
        ordres_termines_result = await db.execute(
            select(Ordres_travail).where(Ordres_travail.statut == "TERMINÉ")
        )
        ordres_termines = len(ordres_termines_result.scalars().all())
        
        ordres_urgents_result = await db.execute(
            select(Ordres_travail).where(Ordres_travail.priorite == "URGENTE")
        )
        ordres_urgents = len(ordres_urgents_result.scalars().all())
        
        # Machine statistics
        total_machines_result = await db.execute(select(Machines))
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
            total_ordres=total_ordres,
            ordres_en_attente=ordres_en_attente,
            ordres_en_cours=ordres_en_cours,
            ordres_termines=ordres_termines,
            ordres_urgents=ordres_urgents,
            total_machines=total_machines,
            machines_en_maintenance=machines_en_maintenance,
            machines_hors_service=machines_hors_service
        )
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/ordres", response_model=List[WorkOrderResponse])
async def get_work_orders(
    statut: Optional[str] = Query(None, description="Filter by status"),
    priorite: Optional[str] = Query(None, description="Filter by priority"),
    machine_id: Optional[int] = Query(None, description="Filter by machine"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-CHETOP-001: Get work orders with filters"""
    try:
        query = select(
            Ordres_travail,
            Machines.nom.label("machine_nom"),
            Utilisateurs.nom.label("utilisateur_nom")
        ).outerjoin(Machines, Ordres_travail.machine_id == Machines.id)\
         .outerjoin(Utilisateurs, Ordres_travail.utilisateur_id == Utilisateurs.id)
        
        # Apply filters
        if statut:
            query = query.where(Ordres_travail.statut == statut)
        if priorite:
            query = query.where(Ordres_travail.priorite == priorite)
        if machine_id:
            query = query.where(Ordres_travail.machine_id == machine_id)
        
        # Order by created_at desc
        query = query.order_by(Ordres_travail.created_at.desc())
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        rows = result.all()
        
        work_orders = []
        for row in rows:
            ordre, machine_nom, utilisateur_nom = row
            work_orders.append(WorkOrderResponse(
                id=ordre.id,
                titre=ordre.titre,
                description=ordre.description,
                priorite=ordre.priorite,
                statut=ordre.statut,
                date_echeance=ordre.date_echeance,
                created_at=ordre.created_at,
                updated_at=ordre.updated_at,
                machine_id=ordre.machine_id,
                machine_nom=machine_nom,
                utilisateur_id=ordre.utilisateur_id,
                utilisateur_nom=utilisateur_nom
            ))
        
        return work_orders
    except Exception as e:
        logger.error(f"Error getting work orders: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/ordres", response_model=WorkOrderResponse, status_code=201)
async def create_work_order(
    data: WorkOrderCreate,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-CHETOP-001: Create new work order"""
    try:
        # Validate machine exists
        machine_result = await db.execute(
            select(Machines).where(Machines.id == data.machine_id)
        )
        machine = machine_result.scalar_one_or_none()
        if not machine:
            raise HTTPException(status_code=404, detail="Machine not found")
        
        # Handle empty string date_echeance
        date_echeance = None if data.date_echeance == "" else data.date_echeance
        
        # Create work order
        new_ordre = Ordres_travail(
            titre=data.titre,
            description=data.description,
            priorite=data.priorite,
            machine_id=data.machine_id,
            utilisateur_id=data.utilisateur_id,
            date_echeance=date_echeance,
            statut="EN_ATTENTE",  # Initial status
            created_by=current_user.id,
        )
        
        db.add(new_ordre)
        await db.commit()
        await db.refresh(new_ordre)
        
        # Publish RabbitMQ event + dispatch Celery email task
        wo_payload = {
            "id": new_ordre.id,
            "titre": new_ordre.titre,
            "description": new_ordre.description,
            "priorite": new_ordre.priorite,
            "machine_id": new_ordre.machine_id,
            "date_echeance": str(new_ordre.date_echeance) if new_ordre.date_echeance else None,
            "statut": new_ordre.statut,
        }
        creator_payload = {"id": current_user.id, "nom": current_user.nom, "email": current_user.email}

        try:
            rmq = await get_rabbitmq()
            await rmq.publish_work_order_event(ROUTING_KEY_WO_CREATED, {
                "work_order": wo_payload,
                "created_by": creator_payload,
            })
        except Exception as rmq_err:
            logger.warning(f"RabbitMQ publish failed (non-blocking): {rmq_err}")

        # Send async email notifications to ChefTech users
        try:
            ct_result = await db.execute(
                select(Utilisateurs).where(Utilisateurs.role == UserRole.CHEFTECH)
            )
            cheftech_users = [
                {"email": u.email, "nom": u.nom} for u in ct_result.scalars().all()
            ]
            if cheftech_users:
                notify_work_order_created.delay(wo_payload, creator_payload, cheftech_users)
        except Exception as task_err:
            logger.warning(f"Celery task dispatch failed (non-blocking): {task_err}")

        # Get related data for response
        machine_result = await db.execute(
            select(Machines.nom).where(Machines.id == new_ordre.machine_id)
        )
        machine_nom = machine_result.scalar_one_or_none()
        
        utilisateur_nom = None
        if new_ordre.utilisateur_id:
            user_result = await db.execute(
                select(Utilisateurs.nom).where(Utilisateurs.id == new_ordre.utilisateur_id)
            )
            utilisateur_nom = user_result.scalar_one_or_none()
        
        return WorkOrderResponse(
            id=new_ordre.id,
            titre=new_ordre.titre,
            description=new_ordre.description,
            priorite=new_ordre.priorite,
            statut=new_ordre.statut,
            date_echeance=new_ordre.date_echeance,
            created_at=new_ordre.created_at,
            updated_at=new_ordre.updated_at,
            machine_id=new_ordre.machine_id,
            machine_nom=machine_nom,
            utilisateur_id=new_ordre.utilisateur_id,
            utilisateur_nom=utilisateur_nom
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating work order: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/ordres/{ordre_id}", response_model=WorkOrderResponse)
async def update_work_order(
    ordre_id: int,
    data: WorkOrderUpdate,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-CHETOP-004: Update work order status and details"""
    try:
        # Get work order
        ordre_result = await db.execute(
            select(Ordres_travail).where(Ordres_travail.id == ordre_id)
        )
        ordre = ordre_result.scalar_one_or_none()
        if not ordre:
            raise HTTPException(status_code=404, detail="Work order not found")
        
        old_status = ordre.statut

        # Update fields
        if data.statut:
            ordre.statut = data.statut
        if data.priorite:
            ordre.priorite = data.priorite
        if data.utilisateur_id is not None:
            ordre.utilisateur_id = data.utilisateur_id
        # Handle empty string date_echeance
        if data.date_echeance == "":
            ordre.date_echeance = None
        elif data.date_echeance:
            ordre.date_echeance = data.date_echeance
        
        await db.commit()
        await db.refresh(ordre)

        # Publish RabbitMQ event if status changed
        if data.statut and data.statut != old_status:
            wo_payload = {
                "id": ordre.id,
                "titre": ordre.titre,
                "priorite": ordre.priorite,
                "statut": ordre.statut,
            }
            changer_payload = {"id": current_user.id, "nom": current_user.nom, "email": current_user.email}

            try:
                rmq = await get_rabbitmq()
                await rmq.publish_work_order_event(ROUTING_KEY_WO_STATUS_CHANGED, {
                    "work_order": wo_payload,
                    "old_status": old_status,
                    "new_status": data.statut,
                    "changed_by": changer_payload,
                })
            except Exception as rmq_err:
                logger.warning(f"RabbitMQ publish failed (non-blocking): {rmq_err}")

            try:
                recipients = []
                if getattr(ordre, "created_by", None):
                    creator_result = await db.execute(
                        select(Utilisateurs).where(Utilisateurs.id == ordre.created_by)
                    )
                    creator = creator_result.scalar_one_or_none()
                    if creator:
                        recipients.append({"email": creator.email, "nom": creator.nom})
                if recipients:
                    notify_work_order_status_changed.delay(
                        wo_payload, old_status, data.statut, changer_payload, recipients
                    )
            except Exception as task_err:
                logger.warning(f"Celery task dispatch failed (non-blocking): {task_err}")
        
        # Get related data for response
        machine_result = await db.execute(
            select(Machines.nom).where(Machines.id == ordre.machine_id)
        )
        machine_nom = machine_result.scalar_one_or_none()
        
        utilisateur_nom = None
        if ordre.utilisateur_id:
            user_result = await db.execute(
                select(Utilisateurs.nom).where(Utilisateurs.id == ordre.utilisateur_id)
            )
            utilisateur_nom = user_result.scalar_one_or_none()
        
        return WorkOrderResponse(
            id=ordre.id,
            titre=ordre.titre,
            description=ordre.description,
            priorite=ordre.priorite,
            statut=ordre.statut,
            date_echeance=ordre.date_echeance,
            created_at=ordre.created_at,
            updated_at=ordre.updated_at,
            machine_id=ordre.machine_id,
            machine_nom=machine_nom,
            utilisateur_id=ordre.utilisateur_id,
            utilisateur_nom=utilisateur_nom
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating work order: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/machines", response_model=List[MachineResponse])
async def get_machines(
    statut: Optional[str] = Query(None, description="Filter by status"),
    type: Optional[str] = Query(None, description="Filter by type"),
    emplacement: Optional[str] = Query(None, description="Filter by location"),
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-CHETOP-006: Get machines with status overview"""
    try:
        query = select(Machines)
        
        if statut:
            query = query.where(Machines.statut == statut)
        if type:
            query = query.where(Machines.type == type)
        if emplacement:
            query = query.where(Machines.emplacement.ilike(f"%{emplacement}%"))
        
        query = query.order_by(Machines.nom)
        
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
