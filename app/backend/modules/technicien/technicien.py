from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.rabbitmq import (
    get_rabbitmq,
    ROUTING_KEY_INT_REQUESTED,
    ROUTING_KEY_INT_STATUS_CHANGED,
)
from models.ordres_intervention import Ordres_intervention
from models.ordres_travail import Ordres_travail
from models.utilisateurs import Utilisateurs, UserRole
from modules.auth.auth import get_current_user
from tasks.intervention_events import (
    notify_intervention_requested,
    notify_intervention_status_changed,
)

router = APIRouter(prefix="/api/v1/technicien", tags=["technicien"])


class InterventionResponse(BaseModel):
    id: int
    ordre_travail_id: int
    statut: str
    date_intervention: datetime
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
    rapport: Optional[str] = None
    work_order_due_date: Optional[datetime] = None
    is_overdue: Optional[bool] = None

    class Config:
        from_attributes = True


class InterventionStatusUpdate(BaseModel):
    statut: str
    rapport: Optional[str] = None


class InterventionRequestPayload(BaseModel):
    ordre_travail_id: int
    machine_id: Optional[int] = None
    problem_description: str
    priority: str
    estimated_duration_minutes: Optional[int] = None
    required_materials: Optional[str] = None


async def verify_technicien(current_user: Utilisateurs = Depends(get_current_user)) -> Utilisateurs:
    if current_user.role != "TECHNICIEN":
        raise HTTPException(status_code=403, detail="Accès non autorisé. Rôle TECHNICIEN requis.")
    return current_user


@router.get("/interventions", response_model=List[InterventionResponse])
async def list_my_interventions(
    statut: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: Utilisateurs = Depends(verify_technicien),
    db: AsyncSession = Depends(get_db),
):
    query = select(Ordres_intervention).where(Ordres_intervention.technicien_id == current_user.id)
    if statut:
        query = query.where(Ordres_intervention.statut == statut)

    query = query.order_by(Ordres_intervention.date_intervention.desc()).offset(skip).limit(limit)
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


@router.put("/interventions/{intervention_id}/status", response_model=InterventionResponse)
async def update_intervention_status(
    intervention_id: int,
    data: InterventionStatusUpdate,
    current_user: Utilisateurs = Depends(verify_technicien),
    db: AsyncSession = Depends(get_db),
):
    intervention = await db.scalar(
        select(Ordres_intervention).where(
            and_(
                Ordres_intervention.id == intervention_id,
                Ordres_intervention.technicien_id == current_user.id,
            )
        )
    )
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")

    # Approval workflow:
    # - Technician can request an intervention start (PENDING_APPROVAL)
    # - Only after approval can they move to EN_COURS
    # - Declined stays DECLINED
    valid_statuses = {"EN_ATTENTE", "EN_COURS", "TERMINÉ", "BLOQUÉ", "PENDING_APPROVAL", "APPROVED", "DECLINED"}
    if data.statut not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid statut. Allowed: {sorted(valid_statuses)}")

    if data.statut == "EN_COURS" and intervention.statut not in {"APPROVED", "EN_COURS"}:
        raise HTTPException(status_code=400, detail="Intervention must be approved by ChefTech before starting")

    if intervention.statut == "DECLINED" and data.statut in {"EN_COURS", "TERMINÉ"}:
        raise HTTPException(status_code=400, detail="Declined intervention cannot be started")

    now = datetime.utcnow()

    old_status = intervention.statut

    intervention.statut = data.statut
    if data.rapport is not None:
        intervention.rapport = data.rapport

    if data.statut == "EN_COURS" and intervention.date_debut is None:
        intervention.date_debut = now

    if data.statut == "TERMINÉ":
        if intervention.date_debut is None:
            intervention.date_debut = now
        intervention.date_fin = intervention.date_fin or now

    if data.statut == "BLOQUÉ":
        if intervention.date_debut is None:
            intervention.date_debut = now

    await db.commit()
    await db.refresh(intervention)

    # RabbitMQ event + Celery email for status change
    if data.statut != old_status:
        int_payload = {
            "id": intervention.id,
            "ordre_travail_id": intervention.ordre_travail_id,
            "statut": intervention.statut,
        }
        changer_payload = {"id": current_user.id, "nom": current_user.nom, "email": current_user.email}

        try:
            rmq = await get_rabbitmq()
            await rmq.publish_intervention_event(ROUTING_KEY_INT_STATUS_CHANGED, {
                "intervention": int_payload,
                "old_status": old_status,
                "new_status": data.statut,
                "changed_by": changer_payload,
            })
        except Exception as rmq_err:
            logger.warning(f"RabbitMQ publish failed (non-blocking): {rmq_err}")

        try:
            ct_result = await db.execute(
                select(Utilisateurs).where(Utilisateurs.role == UserRole.CHEFTECH)
            )
            recipients = [
                {"email": u.email, "nom": u.nom} for u in ct_result.scalars().all()
            ]
            if recipients:
                notify_intervention_status_changed.delay(
                    int_payload, old_status, data.statut, changer_payload, recipients
                )
        except Exception as task_err:
            logger.warning(f"Celery task dispatch failed (non-blocking): {task_err}")

    # Propagate status to the parent work order
    ordre_id = intervention.ordre_travail_id
    ordre = await db.scalar(select(Ordres_travail).where(Ordres_travail.id == ordre_id))
    if ordre:
        stats = await db.execute(
            select(
                func.count(Ordres_intervention.id).label("total"),
                func.sum(case((Ordres_intervention.statut == "TERMINÉ", 1), else_=0)).label("done"),
                func.sum(case((Ordres_intervention.statut == "EN_COURS", 1), else_=0)).label("in_progress"),
                func.sum(case((Ordres_intervention.statut == "BLOQUÉ", 1), else_=0)).label("blocked"),
            ).where(Ordres_intervention.ordre_travail_id == ordre_id)
        )
        row = stats.first()
        total = int((row.total or 0) if row else 0)
        done = int((row.done or 0) if row else 0)
        in_progress = int((row.in_progress or 0) if row else 0)
        blocked = int((row.blocked or 0) if row else 0)

        if blocked > 0:
            ordre.statut = "BLOQUÉ"
        elif in_progress > 0:
            ordre.statut = "EN_COURS"
        elif total > 0 and done == total:
            ordre.statut = "TERMINÉ"
        elif total > 0:
            ordre.statut = "ASSIGNÉ"

        await db.commit()

    return intervention


@router.post("/interventions/request", response_model=InterventionResponse, status_code=201)
async def request_intervention(
    payload: InterventionRequestPayload,
    current_user: Utilisateurs = Depends(verify_technicien),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()

    intervention = await db.scalar(
        select(Ordres_intervention).where(
            and_(
                Ordres_intervention.ordre_travail_id == payload.ordre_travail_id,
                Ordres_intervention.technicien_id == current_user.id,
            )
        )
    )

    if not intervention:
        intervention = Ordres_intervention(
            date_intervention=now,
            ordre_travail_id=payload.ordre_travail_id,
            technicien_id=current_user.id,
            statut="PENDING_APPROVAL",
            requested_at=now,
        )
        db.add(intervention)
        await db.flush()
    else:
        # Allow re-request if previously declined
        if intervention.statut not in {"EN_ATTENTE", "PENDING_APPROVAL", "DECLINED"}:
            raise HTTPException(status_code=400, detail="Intervention cannot be requested in its current status")
        intervention.statut = "PENDING_APPROVAL"
        intervention.requested_at = now
        intervention.approved_by = None
        intervention.approved_at = None
        intervention.rejection_reason = None

    intervention.machine_id = payload.machine_id
    intervention.problem_description = payload.problem_description
    intervention.priority = payload.priority
    intervention.estimated_duration_minutes = payload.estimated_duration_minutes
    intervention.required_materials = payload.required_materials

    await db.commit()
    await db.refresh(intervention)

    # RabbitMQ event + Celery email for intervention request
    int_payload = {
        "id": intervention.id,
        "ordre_travail_id": intervention.ordre_travail_id,
        "statut": intervention.statut,
        "problem_description": payload.problem_description,
        "priority": payload.priority,
        "estimated_duration_minutes": payload.estimated_duration_minutes,
        "required_materials": payload.required_materials,
        "machine_id": payload.machine_id,
    }
    tech_payload = {"id": current_user.id, "nom": current_user.nom, "email": current_user.email}

    try:
        rmq = await get_rabbitmq()
        await rmq.publish_intervention_event(ROUTING_KEY_INT_REQUESTED, {
            "intervention": int_payload,
            "requested_by": tech_payload,
        })
    except Exception as rmq_err:
        logger.warning(f"RabbitMQ publish failed (non-blocking): {rmq_err}")

    try:
        ct_result = await db.execute(
            select(Utilisateurs).where(Utilisateurs.role == UserRole.CHEFTECH)
        )
        cheftech_recipients = [
            {"email": u.email, "nom": u.nom} for u in ct_result.scalars().all()
        ]
        if cheftech_recipients:
            notify_intervention_requested.delay(int_payload, tech_payload, cheftech_recipients)
    except Exception as task_err:
        logger.warning(f"Celery task dispatch failed (non-blocking): {task_err}")

    return intervention
