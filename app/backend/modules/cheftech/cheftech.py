from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, or_, select, func, cast, String
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.rabbitmq import (
    get_rabbitmq,
    ROUTING_KEY_WO_ASSIGNED,
    ROUTING_KEY_INT_APPROVED,
    ROUTING_KEY_INT_DECLINED,
)
from models.ordres_intervention import Ordres_intervention
from models.machines import Machines
from models.ordres_travail import Ordres_travail
from models.utilisateurs import Utilisateurs, UserRole
from modules.auth.auth import get_current_user
from services.notifications import NotificationsService
from tasks.work_order_events import notify_work_order_assigned
from tasks.intervention_events import (
    notify_intervention_approved,
    notify_intervention_declined,
)

router = APIRouter(prefix="/api/v1/cheftech", tags=["cheftech"])

# Pydantic schemas
class InterventionResponse(BaseModel):
    id: int
    date_intervention: datetime
    rapport: Optional[str] = None
    ordre_travail_id: int
    technicien_id: Optional[int] = None
    statut: Optional[str] = None
    problem_description: Optional[str] = None
    priority: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
    required_materials: Optional[str] = None
    machine_id: Optional[int] = None
    requested_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    work_order_due_date: Optional[datetime] = None
    is_overdue: Optional[bool] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class WorkOrderResponse(BaseModel):
    id: int
    titre: str
    description: str
    statut: str
    priorite: str
    machine_id: int
    utilisateur_id: Optional[int] = None
    date_echeance: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class MachineResponse(BaseModel):
    id: int
    nom: str
    emplacement: str
    statut: str
    type: str
    date_derniere_maintenance: Optional[datetime] = None
    date_prochaine_maintenance: Optional[datetime] = None
    image_url: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TechnicianResponse(BaseModel):
    id: int
    nom: str
    email: str
    role: str

    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_interventions: int
    total_ordres_travail: int
    ordres_en_attente: int
    ordres_en_cours: int
    total_techniciens: int
    total_machines: int
    machines_critiques: int

class WorkOrderAssignRequest(BaseModel):
    technicien_ids: List[int]
    estimated_completion_date: Optional[datetime] = None
    machine_ids: Optional[List[int]] = None

# Helper function to check if user has CHEFTECH role
async def verify_cheftech(current_user: Utilisateurs = Depends(get_current_user)):
    if current_user.role != "CHEFTECH":
        raise HTTPException(status_code=403, detail="Accès non autorisé. Rôle CHEFTECH requis.")
    return current_user

async def verify_cheftech_or_admin(current_user: Utilisateurs = Depends(get_current_user)):
    if current_user.role not in ["CHEFTECH", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Accès non autorisé. Rôle CHEFTECH ou ADMIN requis.")
    return current_user

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: Utilisateurs = Depends(verify_cheftech),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard statistics for CHEFTECH"""
    try:
        # Intervention statistics
        total_interventions = await db.scalar(select(func.count(Ordres_intervention.id)))

        # Work order statistics
        total_ordres_travail = await db.scalar(select(func.count(Ordres_travail.id)))
        ordres_en_attente = await db.scalar(
            select(func.count(Ordres_travail.id)).where(Ordres_travail.statut == "EN_ATTENTE")
        )
        ordres_en_cours = await db.scalar(
            select(func.count(Ordres_travail.id)).where(Ordres_travail.statut == "EN_COURS")
        )

        # Technician statistics
        total_techniciens = await db.scalar(
            select(func.count(Utilisateurs.id)).where(cast(Utilisateurs.role, String) == "TECHNICIEN")
        )

        # Machine statistics
        total_machines = await db.scalar(select(func.count(Machines.id)))
        machines_critiques = await db.scalar(
            select(func.count(Machines.id)).where(Machines.statut == "CRITIQUE")
        )

        return DashboardStats(
            total_interventions=total_interventions or 0,
            total_ordres_travail=total_ordres_travail or 0,
            ordres_en_attente=ordres_en_attente or 0,
            ordres_en_cours=ordres_en_cours or 0,
            total_techniciens=total_techniciens or 0,
            total_machines=total_machines or 0,
            machines_critiques=machines_critiques or 0
        )
    except Exception as e:
        print(f"Error in dashboard stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/interventions", response_model=List[InterventionResponse])
async def get_interventions(
    statut: Optional[str] = Query(None, description="Filter by status"),
    current_user: Utilisateurs = Depends(verify_cheftech),
    db: AsyncSession = Depends(get_db),
):
    """Get all interventions (including approval workflow fields)"""
    try:
        query = select(Ordres_intervention)
        if statut:
            query = query.where(Ordres_intervention.statut == statut)
        query = query.order_by(Ordres_intervention.date_intervention.desc())
        result = await db.execute(query)
        interventions = list(result.scalars().all())

        ordre_ids = [i.ordre_travail_id for i in interventions if i.ordre_travail_id is not None]
        due_map = {}
        if ordre_ids:
            ordres_res = await db.execute(
                select(Ordres_travail.id, Ordres_travail.date_echeance).where(Ordres_travail.id.in_(ordre_ids))
            )
            due_map = {row.id: row.date_echeance for row in ordres_res.all()}

        now = datetime.utcnow()
        enriched: List[dict] = []
        for i in interventions:
            due = due_map.get(i.ordre_travail_id)
            is_done = (i.statut or "") in {"TERMINÉ"} or i.date_fin is not None
            status = (i.statut or "")
            eligible = status in {"APPROVED", "EN_COURS", "BLOQUÉ"}
            overdue = bool(eligible and due and (due < now) and (not is_done))

            enriched.append(
                {
                    **InterventionResponse.model_validate(i).model_dump(),
                    "work_order_due_date": due,
                    "is_overdue": overdue,
                }
            )

        return enriched
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


class InterventionDecisionRequest(BaseModel):
    rejection_reason: Optional[str] = None


@router.post("/interventions/{intervention_id}/approve", response_model=InterventionResponse)
async def approve_intervention(
    intervention_id: int,
    current_user: Utilisateurs = Depends(verify_cheftech_or_admin),
    db: AsyncSession = Depends(get_db),
):
    intervention = await db.scalar(select(Ordres_intervention).where(Ordres_intervention.id == intervention_id))
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")

    if intervention.statut != "PENDING_APPROVAL":
        raise HTTPException(status_code=400, detail="Only pending interventions can be approved")

    now = datetime.utcnow()
    intervention.statut = "APPROVED"
    intervention.approved_by = current_user.id
    intervention.approved_at = now
    intervention.rejection_reason = None

    await db.commit()
    await db.refresh(intervention)

    # RabbitMQ event + Celery email for approval
    int_payload = {
        "id": intervention.id,
        "ordre_travail_id": intervention.ordre_travail_id,
        "statut": intervention.statut,
    }
    approver_payload = {"id": current_user.id, "nom": current_user.nom, "email": current_user.email}

    try:
        rmq = await get_rabbitmq()
        await rmq.publish_intervention_event(ROUTING_KEY_INT_APPROVED, {
            "intervention": int_payload,
            "approved_by": approver_payload,
        })
    except Exception as rmq_err:
        logger.warning(f"RabbitMQ publish failed (non-blocking): {rmq_err}")

    try:
        if intervention.technicien_id:
            tech_res = await db.execute(
                select(Utilisateurs).where(Utilisateurs.id == intervention.technicien_id)
            )
            tech_user = tech_res.scalar_one_or_none()
            if tech_user:
                notify_intervention_approved.delay(
                    int_payload,
                    approver_payload,
                    {"email": tech_user.email, "nom": tech_user.nom},
                )
    except Exception as task_err:
        logger.warning(f"Celery task dispatch failed (non-blocking): {task_err}")

    return intervention


@router.post("/interventions/{intervention_id}/reject", response_model=InterventionResponse)
async def reject_intervention(
    intervention_id: int,
    data: InterventionDecisionRequest,
    current_user: Utilisateurs = Depends(verify_cheftech_or_admin),
    db: AsyncSession = Depends(get_db),
):
    intervention = await db.scalar(select(Ordres_intervention).where(Ordres_intervention.id == intervention_id))
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")

    if intervention.statut != "PENDING_APPROVAL":
        raise HTTPException(status_code=400, detail="Only pending interventions can be declined")

    now = datetime.utcnow()
    intervention.statut = "DECLINED"
    intervention.approved_by = current_user.id
    intervention.approved_at = now
    intervention.rejection_reason = data.rejection_reason

    await db.commit()
    await db.refresh(intervention)

    # RabbitMQ event + Celery email for decline
    int_payload = {
        "id": intervention.id,
        "ordre_travail_id": intervention.ordre_travail_id,
        "statut": intervention.statut,
    }
    rejector_payload = {"id": current_user.id, "nom": current_user.nom, "email": current_user.email}

    try:
        rmq = await get_rabbitmq()
        await rmq.publish_intervention_event(ROUTING_KEY_INT_DECLINED, {
            "intervention": int_payload,
            "rejected_by": rejector_payload,
            "reason": data.rejection_reason or "",
        })
    except Exception as rmq_err:
        logger.warning(f"RabbitMQ publish failed (non-blocking): {rmq_err}")

    try:
        if intervention.technicien_id:
            tech_res = await db.execute(
                select(Utilisateurs).where(Utilisateurs.id == intervention.technicien_id)
            )
            tech_user = tech_res.scalar_one_or_none()
            if tech_user:
                notify_intervention_declined.delay(
                    int_payload,
                    rejector_payload,
                    {"email": tech_user.email, "nom": tech_user.nom},
                    data.rejection_reason or "",
                )
    except Exception as task_err:
        logger.warning(f"Celery task dispatch failed (non-blocking): {task_err}")

    return intervention

@router.get("/ordres-travail", response_model=List[WorkOrderResponse])
async def get_work_orders(
    statut: Optional[str] = Query(None, description="Filter by status"),
    current_user: Utilisateurs = Depends(verify_cheftech),
    db: AsyncSession = Depends(get_db)
):
    """Get work orders with optional status filter"""
    try:
        query = select(Ordres_travail)

        # Apply filter
        if statut:
            query = query.where(Ordres_travail.statut == statut)

        query = query.order_by(Ordres_travail.created_at.desc())
        result = await db.execute(query)

        work_orders = [
            WorkOrderResponse(
                id=ordre.id,
                titre=ordre.titre,
                description=ordre.description,
                statut=ordre.statut,
                priorite=ordre.priorite,
                machine_id=ordre.machine_id,
                utilisateur_id=ordre.utilisateur_id,
                date_echeance=ordre.date_echeance,
                created_at=ordre.created_at,
                updated_at=ordre.updated_at
            )
            for ordre in result.scalars()
        ]

        return work_orders
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/techniciens", response_model=List[TechnicianResponse])
async def get_technicians(
    current_user: Utilisateurs = Depends(verify_cheftech),
    db: AsyncSession = Depends(get_db)
):
    """Get all technicians"""
    try:
        query = select(Utilisateurs).where(cast(Utilisateurs.role, String) == "TECHNICIEN")
        query = query.order_by(Utilisateurs.nom)
        result = await db.execute(query)

        technicians = [
            TechnicianResponse(
                id=tech.id,
                nom=tech.nom,
                email=tech.email,
                role=tech.role
            )
            for tech in result.scalars()
        ]

        return technicians
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/machines", response_model=List[MachineResponse])
async def get_machines(
    statut: Optional[str] = Query(None, description="Filter by status"),
    current_user: Utilisateurs = Depends(verify_cheftech),
    db: AsyncSession = Depends(get_db)
):
    """Get machines with optional status filter"""
    try:
        query = select(Machines)

        # Apply filter
        if statut:
            query = query.where(Machines.statut == statut)

        query = query.order_by(Machines.nom)
        result = await db.execute(query)

        machines = [
            MachineResponse(
                id=machine.id,
                nom=machine.nom,
                emplacement=machine.emplacement,
                statut=machine.statut,
                type=machine.type,
                date_derniere_maintenance=machine.date_derniere_maintenance,
                date_prochaine_maintenance=machine.date_prochaine_maintenance,
                image_url=machine.image_url,
                created_at=machine.created_at
            )
            for machine in result.scalars()
        ]

        return machines
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/ordres-travail/{ordre_id}/assign")
async def assign_work_order(
    ordre_id: int,
    data: WorkOrderAssignRequest,
    current_user: Utilisateurs = Depends(verify_cheftech_or_admin),
    db: AsyncSession = Depends(get_db),
):
    if not data.technicien_ids:
        raise HTTPException(status_code=400, detail="technicien_ids is required")

    ordre = await db.scalar(select(Ordres_travail).where(Ordres_travail.id == ordre_id))
    if not ordre:
        raise HTTPException(status_code=404, detail="Work order not found")

    machine_ids = (
        [mid for mid in (data.machine_ids or []) if isinstance(mid, int)]
        if data.machine_ids is not None
        else []
    )
    if not machine_ids:
        machine_ids = [ordre.machine_id]

    machine_ids = sorted(set(machine_ids))

    machine_result = await db.execute(select(Machines.id).where(Machines.id.in_(machine_ids)))
    found_machine_ids = set(machine_result.scalars().all())
    missing_machines = [mid for mid in machine_ids if mid not in found_machine_ids]
    if missing_machines:
        raise HTTPException(status_code=400, detail=f"Invalid machine ids: {missing_machines}")

    tech_result = await db.execute(
        select(Utilisateurs.id).where(
            and_(
                Utilisateurs.id.in_(data.technicien_ids),
                cast(Utilisateurs.role, String) == "TECHNICIEN",
            )
        )
    )
    found_ids = set(tech_result.scalars().all())
    missing = [tid for tid in data.technicien_ids if tid not in found_ids]
    if missing:
        raise HTTPException(status_code=400, detail=f"Invalid technician ids: {missing}")

    now = datetime.utcnow()
    assigned_order_ids: List[int] = []

    for idx, machine_id in enumerate(machine_ids):
        if idx == 0:
            target_ordre = ordre
            target_ordre.machine_id = machine_id
        else:
            target_ordre = Ordres_travail(
                titre=ordre.titre,
                description=ordre.description,
                priorite=ordre.priorite,
                machine_id=machine_id,
                utilisateur_id=ordre.utilisateur_id,
                date_echeance=ordre.date_echeance,
                statut=ordre.statut,
                created_by=ordre.created_by,
                validated_by=ordre.validated_by,
                date_validation=ordre.date_validation,
                estimated_duration=ordre.estimated_duration,
            )
            db.add(target_ordre)
            await db.flush()

        target_ordre.statut = "ASSIGNÉ"
        target_ordre.validated_by = current_user.id
        target_ordre.date_validation = target_ordre.date_validation or now
        if data.estimated_completion_date:
            target_ordre.date_echeance = data.estimated_completion_date

        for technicien_id in data.technicien_ids:
            existing = await db.scalar(
                select(Ordres_intervention).where(
                    and_(
                        Ordres_intervention.ordre_travail_id == target_ordre.id,
                        Ordres_intervention.technicien_id == technicien_id,
                    )
                )
            )
            if existing:
                continue
            db.add(
                Ordres_intervention(
                    date_intervention=now,
                    ordre_travail_id=target_ordre.id,
                    technicien_id=technicien_id,
                    statut="EN_ATTENTE",
                )
            )

        assigned_order_ids.append(target_ordre.id)

    await db.commit()

    notif_service = NotificationsService(db)
    notif_now = datetime.utcnow()

    # Notify technicians
    for tech_id in sorted(set(data.technicien_ids)):
        await notif_service.create(
            {
                "utilisateur_id": tech_id,
                "titre": "Work Order Assigned",
                "priorite": ordre.priorite,
                "type": "WORK_ORDER_ASSIGNED",
                "message": f"Work order #{assigned_order_ids[0]} assigned to you.",
                "date_envoi": notif_now,
                "lu": False,
                "created_at": notif_now,
            }
        )

    # Notify ChefOp (creator)
    if getattr(ordre, "created_by", None):
        await notif_service.create(
            {
                "utilisateur_id": ordre.created_by,
                "titre": "Work Order Assigned",
                "priorite": ordre.priorite,
                "type": "WORK_ORDER_ASSIGNED",
                "message": f"Work order #{assigned_order_ids[0]} has been assigned by ChefTech.",
                "date_envoi": notif_now,
                "lu": False,
                "created_at": notif_now,
            }
        )

    # RabbitMQ event + Celery email for work order assignment
    wo_payload = {
        "id": ordre.id,
        "titre": ordre.titre,
        "description": ordre.description,
        "priorite": ordre.priorite,
        "statut": ordre.statut,
    }
    assigner_payload = {"id": current_user.id, "nom": current_user.nom, "email": current_user.email}

    try:
        rmq = await get_rabbitmq()
        await rmq.publish_work_order_event(ROUTING_KEY_WO_ASSIGNED, {
            "work_order": wo_payload,
            "assigned_by": assigner_payload,
            "technicien_ids": data.technicien_ids,
            "assigned_order_ids": assigned_order_ids,
        })
    except Exception as rmq_err:
        logger.warning(f"RabbitMQ publish failed (non-blocking): {rmq_err}")

    try:
        tech_result_notif = await db.execute(
            select(Utilisateurs).where(Utilisateurs.id.in_(data.technicien_ids))
        )
        tech_recipients = [
            {"email": u.email, "nom": u.nom} for u in tech_result_notif.scalars().all()
        ]
        creator_recipient = None
        if getattr(ordre, "created_by", None):
            creator_res = await db.execute(
                select(Utilisateurs).where(Utilisateurs.id == ordre.created_by)
            )
            creator_user = creator_res.scalar_one_or_none()
            if creator_user:
                creator_recipient = {"email": creator_user.email, "nom": creator_user.nom}

        if tech_recipients:
            notify_work_order_assigned.delay(
                wo_payload, assigner_payload, tech_recipients, creator_recipient
            )
    except Exception as task_err:
        logger.warning(f"Celery task dispatch failed (non-blocking): {task_err}")

    return {
        "message": "Work order assigned",
        "ordre_id": ordre_id,
        "assigned_order_ids": assigned_order_ids,
        "technicien_ids": data.technicien_ids,
        "machine_ids": machine_ids,
    }

@router.put("/machines/{machine_id}/status")
async def update_machine_status(
    machine_id: int,
    statut: str,
    current_user: Utilisateurs = Depends(verify_cheftech),
    db: AsyncSession = Depends(get_db)
):
    """Update machine status"""
    try:
        machine = await db.scalar(select(Machines).where(Machines.id == machine_id))
        if not machine:
            raise HTTPException(status_code=404, detail="Machine non trouvée")

        valid_statuses = ["ACTIF", "INACTIF", "MAINTENANCE", "CRITIQUE", "HORS_SERVICE"]
        if statut not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Statut invalide. Valeurs valides: {valid_statuses}")

        machine.statut = statut
        await db.commit()
        return {"message": "Statut de la machine mis à jour avec succès"}
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

# Export router
router
