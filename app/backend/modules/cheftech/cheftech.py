from datetime import datetime, timezone
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, or_, select, func, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from schemas.pagination import PaginatedResponse

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
from core.auth import get_current_user
from services.notifications import NotificationsService
from tasks.work_order_events import notify_work_order_assigned
from tasks.intervention_events import (
    notify_intervention_approved,
    notify_intervention_declined,
)

router = APIRouter(prefix="/api/v1/cheftech", tags=["cheftech"])

# Set up logging
logger = logging.getLogger(__name__)

# Pydantic schemas
class InterventionResponse(BaseModel):
    id: int
    date_intervention: datetime
    rapport: Optional[str] = None
    ordre_travail_id: Optional[int] = None
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
    updated_at: Optional[datetime] = None

    # PDCA / Enhanced Fields
    actual_failure_type: Optional[str] = None
    ml_prediction_matched: Optional[bool] = None
    retrained: Optional[bool] = None
    machine_category: Optional[str] = None
    symptoms: Optional[str] = None
    problem_start_time: Optional[datetime] = None
    frequency: Optional[str] = None
    operating_state: Optional[str] = None
    temperature: Optional[str] = None
    impact: Optional[str] = None
    estimated_loss: Optional[str] = None
    similar_issue_before: Optional[bool] = None
    suggested_cause: Optional[str] = None
    suggested_priority: Optional[str] = None
    risk_score: Optional[str] = None
    intervention_type: Optional[str] = None
    root_cause_category: Optional[str] = None
    root_cause_description: Optional[str] = None
    actions_performed: Optional[str] = None
    parts_replaced: Optional[str] = None
    tools_used: Optional[str] = None
    machine_status_after: Optional[str] = None
    plan_hypothesis: Optional[str] = None
    check_resolved: Optional[bool] = None
    check_verification_method: Optional[str] = None
    act_preventive_actions: Optional[str] = None
    act_recommendations: Optional[str] = None

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
    emplacement: Optional[str] = None
    statut: Optional[str] = None
    type: Optional[str] = None
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
    total_ordres_travail: int
    ordres_en_attente: int
    ordres_en_cours: int
    total_interventions: int
    interventions_en_cours: int
    total_techniciens: int
    techniciens_disponibles: int
    total_machines: int
    machines_critiques: int

class WorkOrderAssignRequest(BaseModel):
    technicien_ids: List[int]
    estimated_completion_date: Optional[datetime] = None
    machine_ids: Optional[List[int]] = None

async def verify_management_access(current_user: Utilisateurs = Depends(get_current_user)):
    if current_user.role not in [UserRole.CHEFTECH, UserRole.ADMIN, UserRole.CHETOP]:
        raise HTTPException(status_code=403, detail="Accès non autorisé. Rôle de gestion requis.")
    return current_user

async def verify_cheftech(current_user: Utilisateurs = Depends(verify_management_access)):
    return current_user

async def verify_cheftech_or_admin(current_user: Utilisateurs = Depends(verify_management_access)):
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
        interventions_en_cours = await db.scalar(
            select(func.count(Ordres_intervention.id)).where(Ordres_intervention.statut == "EN_COURS")
        )

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
        # Assuming available means active and not currently assigned to an 'EN_COURS' intervention?
        # For now, let's just count all technicians as 'available' or add a proper status if exists.
        # Based on DashboardStatsCards.tsx, it uses 'techniciens_disponibles'
        techniciens_disponibles = total_techniciens # Placeholder or implement proper logic

        # Machine statistics
        total_machines = await db.scalar(select(func.count(Machines.id)))
        machines_critiques = await db.scalar(
            select(func.count(Machines.id)).where(Machines.statut == "CRITIQUE")
        )

        return DashboardStats(
            total_interventions=total_interventions or 0,
            interventions_en_cours=interventions_en_cours or 0,
            total_ordres_travail=total_ordres_travail or 0,
            ordres_en_attente=ordres_en_attente or 0,
            ordres_en_cours=ordres_en_cours or 0,
            total_techniciens=total_techniciens or 0,
            techniciens_disponibles=techniciens_disponibles or 0,
            total_machines=total_machines or 0,
            machines_critiques=machines_critiques or 0
        )
    except Exception as e:
        print(f"Error in dashboard stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/interventions", response_model=PaginatedResponse[InterventionResponse])
async def get_interventions(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    statut: Optional[str] = Query(None, description="Filter by status"),
    current_user: Utilisateurs = Depends(verify_cheftech),
    db: AsyncSession = Depends(get_db),
):
    """Get all interventions (including approval workflow fields)"""
    try:
        skip = (page - 1) * size
        
        # Count total - only show interventions where current user is involved
        count_query = select(func.count(Ordres_intervention.id))\
            .outerjoin(Ordres_travail, Ordres_intervention.ordre_travail_id == Ordres_travail.id)\
            .where(
                or_(
                    Ordres_intervention.technicien_id == current_user.id,
                    Ordres_travail.created_by == current_user.id
                )
            )
        if statut:
            count_query = count_query.where(Ordres_intervention.statut == statut)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = select(Ordres_intervention)\
            .outerjoin(Ordres_travail, Ordres_intervention.ordre_travail_id == Ordres_travail.id)\
            .where(
                or_(
                    Ordres_intervention.technicien_id == current_user.id,
                    Ordres_travail.created_by == current_user.id
                )
            )
        if statut:
            query = query.where(Ordres_intervention.statut == statut)
        query = query.options(
            selectinload(Ordres_intervention.machine),
            selectinload(Ordres_intervention.technicien),
            selectinload(Ordres_intervention.ordre_travail),
        )
        query = query.order_by(Ordres_intervention.date_intervention.desc()).offset(skip).limit(size)
        result = await db.execute(query)
        interventions = list(result.scalars().all())

        ordre_ids = [i.ordre_travail_id for i in interventions if i.ordre_travail_id is not None]
        due_map = {}
        if ordre_ids:
            ordres_res = await db.execute(
                select(Ordres_travail.id, Ordres_travail.date_echeance).where(Ordres_travail.id.in_(ordre_ids))
            )
            due_map = {row.id: row.date_echeance for row in ordres_res.all()}

        now = datetime.now(timezone.utc)
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

        return PaginatedResponse.create(
            items=enriched,
            total=total,
            page=page,
            size=size
        )
    except Exception as e:
        logger.error(f"Error loading interventions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


class InterventionDecisionRequest(BaseModel):
    rejection_reason: Optional[str] = None
    technician_id: Optional[int] = None


@router.get("/ordres-travail", response_model=PaginatedResponse[WorkOrderResponse])
async def get_work_orders(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    statut: Optional[str] = Query(None, description="Filter by status"),
    current_user: Utilisateurs = Depends(verify_cheftech),
    db: AsyncSession = Depends(get_db)
):
    """Get work orders with optional status filter"""
    try:
        skip = (page - 1) * size
        
        # Count total
        count_query = select(func.count(Ordres_travail.id))
        if statut:
            count_query = count_query.where(Ordres_travail.statut == statut)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = select(Ordres_travail)

        # Apply filter
        if statut:
            query = query.where(Ordres_travail.statut == statut)

        query = query.options(
            selectinload(Ordres_travail.machine),
            selectinload(Ordres_travail.utilisateur),
        )
        query = query.order_by(Ordres_travail.created_at.desc()).offset(skip).limit(size)
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

        return PaginatedResponse.create(
            items=work_orders,
            total=total,
            page=page,
            size=size
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/techniciens", response_model=PaginatedResponse[TechnicianResponse])
async def get_technicians(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    current_user: Utilisateurs = Depends(verify_cheftech),
    db: AsyncSession = Depends(get_db)
):
    """Get all technicians"""
    try:
        skip = (page - 1) * size
        
        # Count total
        count_query = select(func.count(Utilisateurs.id)).where(cast(Utilisateurs.role, String) == "TECHNICIEN")
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = select(Utilisateurs).where(cast(Utilisateurs.role, String) == "TECHNICIEN")
        query = query.order_by(Utilisateurs.nom).offset(skip).limit(size)
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

        return PaginatedResponse.create(
            items=technicians,
            total=total,
            page=page,
            size=size
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/machines", response_model=PaginatedResponse[MachineResponse])
async def get_machines(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    statut: Optional[str] = Query(None, description="Filter by status"),
    current_user: Utilisateurs = Depends(verify_cheftech),
    db: AsyncSession = Depends(get_db)
):
    """Get machines with optional status filter"""
    try:
        skip = (page - 1) * size
        
        # Count total
        count_query = select(func.count(Machines.id))
        if statut:
            count_query = count_query.where(Machines.statut == statut)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = select(Machines)

        # Apply filter
        if statut:
            query = query.where(Machines.statut == statut)

        query = query.order_by(Machines.nom).offset(skip).limit(size)
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

        return PaginatedResponse.create(
            items=machines,
            total=total,
            page=page,
            size=size
        )
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

    now = datetime.now(timezone.utc)
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
    notif_now = datetime.now(timezone.utc)

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
    payload: dict,
    current_user: Utilisateurs = Depends(verify_cheftech),
    db: AsyncSession = Depends(get_db)
):
    """Update machine status"""
    statut = payload.get("statut")
    if not statut:
        raise HTTPException(status_code=400, detail="Le champ 'statut' est requis")
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


# ── Completed Work Orders & Feedback ────────────────────────────────────────

class ChefTechFeedbackRequest(BaseModel):
    feedback: str


class CompletedWorkOrderItem(BaseModel):
    id: int
    titre: str
    description: str
    statut: str
    priorite: str
    machine_id: int
    machine_nom: Optional[str] = None
    utilisateur_id: Optional[int] = None
    technician_nom: Optional[str] = None
    technician_email: Optional[str] = None
    date_echeance: Optional[datetime] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    rapport: Optional[str] = None
    failure_type: Optional[str] = None
    cheftech_feedback: Optional[str] = None
    created_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None


@router.get("/completed-work-orders", response_model=PaginatedResponse[CompletedWorkOrderItem])
async def get_completed_work_orders(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    technician_id: Optional[int] = Query(None),
    machine_id: Optional[int] = Query(None),
    failure_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    current_user: Utilisateurs = Depends(verify_cheftech_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get all completed Work Orders enriched with technician and machine info."""
    skip = (page - 1) * size
    
    # Count total with filters
    count_query = select(func.count(Ordres_travail.id)).where(Ordres_travail.statut == "TERMINE")
    if technician_id:
        count_query = count_query.where(Ordres_travail.utilisateur_id == technician_id)
    if machine_id:
        count_query = count_query.where(Ordres_travail.machine_id == machine_id)
    if failure_type:
        count_query = count_query.where(Ordres_travail.failure_type == failure_type)
    if date_from:
        count_query = count_query.where(Ordres_travail.date_fin >= date_from)
    if date_to:
        count_query = count_query.where(Ordres_travail.date_fin <= date_to)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = select(Ordres_travail).where(Ordres_travail.statut == "TERMINE")
    query = query.options(
        selectinload(Ordres_travail.machine),
        selectinload(Ordres_travail.utilisateur),
    )

    if technician_id:
        query = query.where(Ordres_travail.utilisateur_id == technician_id)
    if machine_id:
        query = query.where(Ordres_travail.machine_id == machine_id)
    if failure_type:
        query = query.where(Ordres_travail.failure_type == failure_type)
    if date_from:
        query = query.where(Ordres_travail.date_fin >= date_from)
    if date_to:
        query = query.where(Ordres_travail.date_fin <= date_to)

    query = query.order_by(Ordres_travail.date_fin.desc()).offset(skip).limit(size)
    result = await db.execute(query)
    work_orders = list(result.scalars().all())

    # Enrich with technician and machine names
    user_ids = list({wo.utilisateur_id for wo in work_orders if wo.utilisateur_id})
    machine_ids = list({wo.machine_id for wo in work_orders if wo.machine_id})

    user_map: dict = {}
    machine_map: dict = {}

    if user_ids:
        users_res = await db.execute(
            select(Utilisateurs.id, Utilisateurs.nom, Utilisateurs.email).where(Utilisateurs.id.in_(user_ids))
        )
        for row in users_res.all():
            user_map[row.id] = {"nom": row.nom, "email": row.email}

    if machine_ids:
        machines_res = await db.execute(
            select(Machines.id, Machines.nom).where(Machines.id.in_(machine_ids))
        )
        for row in machines_res.all():
            machine_map[row.id] = row.nom

    items = []
    for wo in work_orders:
        duration = None
        if wo.date_debut and wo.date_fin:
            delta = wo.date_fin - wo.date_debut
            duration = int(delta.total_seconds() / 60)

        tech = user_map.get(wo.utilisateur_id, {})
        items.append(CompletedWorkOrderItem(
            id=wo.id,
            titre=wo.titre,
            description=wo.description,
            statut=wo.statut,
            priorite=wo.priorite,
            machine_id=wo.machine_id,
            machine_nom=machine_map.get(wo.machine_id),
            utilisateur_id=wo.utilisateur_id,
            technician_nom=tech.get("nom"),
            technician_email=tech.get("email"),
            date_echeance=wo.date_echeance,
            date_debut=wo.date_debut,
            date_fin=wo.date_fin,
            rapport=wo.rapport,
            failure_type=wo.failure_type,
            cheftech_feedback=wo.cheftech_feedback,
            created_at=wo.created_at,
            duration_minutes=duration,
        ))

    return items


@router.put("/work-orders/{ordre_id}/feedback")
async def add_cheftech_feedback(
    ordre_id: int,
    data: ChefTechFeedbackRequest,
    current_user: Utilisateurs = Depends(verify_cheftech_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Add ChefTech feedback to a completed Work Order. Does not alter execution data."""
    if current_user.role not in [UserRole.CHEFTECH, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Accès refusé. ChefTech ou Admin requis.")

    ordre = await db.scalar(select(Ordres_travail).where(Ordres_travail.id == ordre_id))
    if not ordre:
        raise HTTPException(status_code=404, detail="Ordre de travail non trouvé")

    if ordre.statut != "TERMINE":
        raise HTTPException(status_code=400, detail="Le feedback ne peut être ajouté qu'aux ordres terminés")

    ordre.cheftech_feedback = data.feedback.strip()
    await db.commit()

    return {"status": "success", "ordre_id": ordre_id, "feedback": ordre.cheftech_feedback}


@router.get("/reports/kpi")
async def get_kpi_report(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    current_user: Utilisateurs = Depends(verify_cheftech_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """KPI summary for completed Work Orders. Available to ChefTech and Admin."""
    base_query = select(Ordres_travail).where(Ordres_travail.statut == "TERMINE")
    base_query = base_query.options(
        selectinload(Ordres_travail.machine),
        selectinload(Ordres_travail.utilisateur),
    )
    if date_from:
        base_query = base_query.where(Ordres_travail.date_fin >= date_from)
    if date_to:
        base_query = base_query.where(Ordres_travail.date_fin <= date_to)

    result = await db.execute(base_query)
    completed = list(result.scalars().all())

    total = len(completed)
    durations = [
        int((wo.date_fin - wo.date_debut).total_seconds() / 60)
        for wo in completed
        if wo.date_debut and wo.date_fin
    ]
    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0

    failure_counts: dict = {}
    for wo in completed:
        ft = wo.failure_type or "NONE"
        failure_counts[ft] = failure_counts.get(ft, 0) + 1

    feedback_count = sum(1 for wo in completed if wo.cheftech_feedback)

    return {
        "total_completed": total,
        "avg_duration_minutes": avg_duration,
        "failures_by_type": failure_counts,
        "feedback_count": feedback_count,
        "feedback_coverage_pct": round((feedback_count / total * 100) if total else 0, 1),
    }


@router.get("/analytics/dashboard")
async def get_cheftech_analytics_dashboard(
    current_user: Utilisateurs = Depends(verify_cheftech_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns analytics and PDCA metrics for the ChefTech dashboard.
    For simplicity in this MVP, we query all work orders and interventions
    to compute the PDCA stages and performance trends.
    """
    # 1. Fetch all work orders and interventions
    w_result = await db.execute(
        select(Ordres_travail)
        .options(selectinload(Ordres_travail.machine))
        .options(selectinload(Ordres_travail.utilisateur))
    )
    all_wos = list(w_result.scalars().all())

    i_result = await db.execute(
        select(Ordres_intervention)
        .options(selectinload(Ordres_intervention.machine))
        .options(selectinload(Ordres_intervention.technicien))
    )
    all_ints = list(i_result.scalars().all())

    # Metrics computation
    total_assigned = len(all_wos)
    completed_wos = [wo for wo in all_wos if wo.statut == "TERMINE"]
    pending_wos = [wo for wo in all_wos if wo.statut == "A FAIRE"]
    in_progress_wos = [wo for wo in all_wos if wo.statut == "EN_COURS"]

    durations = [
        int((wo.date_fin - wo.date_debut).total_seconds() / 60)
        for wo in completed_wos
        if wo.date_debut and wo.date_fin
    ]
    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0

    failure_counts = {}
    for wo in completed_wos:
        ft = wo.failure_type or "NONE"
        failure_counts[ft] = failure_counts.get(ft, 0) + 1

    # PDCA Lifecycle
    # Plan: Interventions pending validation
    pdca_plan = sum(1 for i in all_ints if i.statut == "EN_ATTENTE")
    # Do: Work Orders assigned or in progress
    pdca_do = len(pending_wos) + len(in_progress_wos)
    # Check: Work Orders completed (total completed)
    pdca_check = len(completed_wos)
    # Act: Work Orders with ChefTech feedback
    pdca_act = sum(1 for wo in completed_wos if wo.cheftech_feedback)

    # Trend: Completions per day (simple aggregation for the charts)
    trend_dict = {}
    for wo in completed_wos:
        if wo.date_fin:
            day_str = wo.date_fin.strftime("%Y-%m-%d")
            trend_dict[day_str] = trend_dict.get(day_str, 0) + 1

    # Sort trend for chart rendering
    trend_chart = [
        {"date": date_str, "completed": count}
        for date_str, count in sorted(trend_dict.items())
    ]

    return {
        "summary": {
            "total_assigned": total_assigned,
            "completed": len(completed_wos),
            "pending": len(pending_wos),
            "in_progress": len(in_progress_wos),
            "avg_duration": avg_duration,
            "failure_types": failure_counts,
        },
        "pdca": {
            "plan": pdca_plan,
            "do": pdca_do,
            "check": pdca_check,
            "act": pdca_act,
        },
        "trends": trend_chart,
        "alerts": {
            "late_wos": sum(1 for wo in completed_wos if wo.date_fin and wo.date_echeance and wo.date_fin > wo.date_echeance),
            "top_failure": max(failure_counts, key=failure_counts.get) if failure_counts else "N/A"
        }
    }
