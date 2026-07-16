import logging
from datetime import datetime, timezone
from typing import List, Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from schemas.pagination import PaginatedResponse

from core.database import get_db
from core.rabbitmq import (
    get_rabbitmq,
    ROUTING_KEY_INT_REQUESTED,
    ROUTING_KEY_INT_STATUS_CHANGED,
)
from models.OrdresIntervention import OrdresIntervention
from models.OrdresTravail import OrdresTravail
from models.PlanningTaches import PlanningTaches
from models.utilisateurs import Utilisateurs, UserRole
from core.security import verify_technicien
from tasks.intervention_events import (
    notify_intervention_requested,
    notify_intervention_status_changed,
)
from ..schemas import (
    InterventionResponse,
    InterventionStatusUpdate,
    InterventionRequestPayload,
)

router = APIRouter(prefix="/api/v1/technicien", tags=["technicien"])
logger = logging.getLogger(__name__)

_STATUT_TERMINE = "TERMINÉ"
_STATUT_BLOQUE = "BLOQUÉ"


@router.get("/interventions", response_model=PaginatedResponse[InterventionResponse])
async def list_my_interventions(
    *, page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 10,
    statut: Annotated[Optional[str], Query(description="Filter by status")] = None,
    _current_user: Annotated[Utilisateurs, Depends(verify_technicien)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    skip = (page - 1) * size

    # Count total
    count_query = (
        select(func.count(OrdresIntervention.id))
        .where(OrdresIntervention.technician_id == _current_user.id)
        .where(OrdresIntervention.archived_at.is_(None))
    )
    if statut:
        count_query = count_query.where(OrdresIntervention.statut == statut)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = (
        select(OrdresIntervention)
        .where(OrdresIntervention.technician_id == _current_user.id)
        .where(OrdresIntervention.archived_at.is_(None))
    )
    if statut:
        query = query.where(OrdresIntervention.statut == statut)

    query = query.options(
        selectinload(OrdresIntervention.machine),
        selectinload(OrdresIntervention.ordre_travail),
    )
    query = (
        query.order_by(OrdresIntervention.date_intervention.desc())
        .offset(skip)
        .limit(size)
    )
    # nosemgrep: python.fastapi.db.generic-sql-fastapi -- `query` is a SQLAlchemy
    # Core select() built from ORM column comparisons above (technician_id/statut
    # bound via ==); no raw SQL or string interpolation is involved.
    result = await db.execute(query)
    interventions = list(result.scalars().all())

    ordre_ids = [
        i.ordre_travail_id for i in interventions if i.ordre_travail_id is not None
    ]
    due_map = {}
    if ordre_ids:
        ordres_res = await db.execute(
            select(OrdresTravail.id, OrdresTravail.date_echeance).where(
                OrdresTravail.id.in_(ordre_ids)
            )
        )
        due_map = {row.id: row.date_echeance for row in ordres_res.all()}

    now = datetime.now(timezone.utc)
    enriched: List[dict] = []
    for i in interventions:
        due = due_map.get(i.ordre_travail_id)
        is_done = (i.statut or "") in {_STATUT_TERMINE} or i.date_fin is not None
        status = i.statut or ""
        eligible = status in {"APPROVED", "EN_COURS", _STATUT_BLOQUE}
        overdue = bool(eligible and due and (due < now) and (not is_done))

        enriched.append(
            {
                **InterventionResponse.model_validate(i).model_dump(),
                "work_order_due_date": due,
                "is_overdue": overdue,
            }
        )

    return PaginatedResponse.create(items=enriched, total=total, page=page, size=size)


_VALID_STATUSES = {"EN_ATTENTE", "EN_COURS", _STATUT_TERMINE, _STATUT_BLOQUE, "PENDING_APPROVAL", "APPROVED", "DECLINED"}


def _validate_status_transition(intervention: OrdresIntervention, data: "InterventionStatusUpdate") -> None:
    """Raise HTTPException if the requested status transition is forbidden."""
    if data.statut not in _VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid statut. Allowed: {sorted(_VALID_STATUSES)}")
    if data.statut == "EN_COURS" and intervention.statut not in {"APPROVED", "EN_COURS"}:
        raise HTTPException(status_code=400, detail="Intervention must be approved by ChefTech before starting")
    if intervention.statut == "DECLINED" and data.statut in {"EN_COURS", _STATUT_TERMINE}:
        raise HTTPException(status_code=400, detail="Declined intervention cannot be started")


def _apply_intervention_dates(intervention: OrdresIntervention, data: "InterventionStatusUpdate", now: datetime) -> None:
    """Set date_debut / date_fin based on the new status."""
    if data.statut == "EN_COURS" and intervention.date_debut is None:
        intervention.date_debut = data.date_debut or now
    elif data.statut == _STATUT_TERMINE:
        intervention.date_debut = data.date_debut or intervention.date_debut or now
        intervention.date_fin = data.date_fin or intervention.date_fin or now
    elif data.statut == _STATUT_BLOQUE:
        if intervention.date_debut is None:
            intervention.date_debut = data.date_debut or now


async def _notify_status_change(db: AsyncSession, current_user: Utilisateurs,
                                 intervention: OrdresIntervention, old_status: str, new_status: str) -> None:
    """Publish RabbitMQ event and dispatch Celery email (both non-fatal)."""
    int_payload = {"id": intervention.id, "ordre_travail_id": intervention.ordre_travail_id, "statut": new_status}
    changer_payload = {"id": current_user.id, "nom": current_user.nom, "email": current_user.email}

    try:
        rmq = await get_rabbitmq()
        await rmq.publish_intervention_event(
            ROUTING_KEY_INT_STATUS_CHANGED,
            {"intervention": int_payload, "old_status": old_status, "new_status": new_status, "changed_by": changer_payload},
        )
    except Exception as rmq_err:
        logger.warning(f"RabbitMQ publish failed (non-blocking): {rmq_err}")

    try:
        ct_result = await db.execute(select(Utilisateurs).where(Utilisateurs.role == UserRole.CHEFTECH))
        recipients = [{"email": u.email, "nom": u.nom} for u in ct_result.scalars().all()]
        if recipients:
            notify_intervention_status_changed.delay(int_payload, old_status, new_status, changer_payload, recipients)
    except Exception as task_err:
        logger.warning(f"Celery task dispatch failed (non-blocking): {task_err}")


async def _propagate_wo_status(db: AsyncSession, ordre_id: int) -> None:
    """Update parent work order status based on linked intervention stats."""
    ordre = await db.scalar(select(OrdresTravail).where(OrdresTravail.id == ordre_id))
    if not ordre:
        return
    stats = await db.execute(
        select(
            func.count(OrdresIntervention.id).label("total"),
            func.sum(case((OrdresIntervention.statut == _STATUT_TERMINE, 1), else_=0)).label("done"),
            func.sum(case((OrdresIntervention.statut == "EN_COURS", 1), else_=0)).label("in_progress"),
            func.sum(case((OrdresIntervention.statut == _STATUT_BLOQUE, 1), else_=0)).label("blocked"),
        ).where(OrdresIntervention.ordre_travail_id == ordre_id)
    )
    row = stats.first()
    total = int((row.total or 0) if row else 0)
    done = int((row.done or 0) if row else 0)
    in_progress = int((row.in_progress or 0) if row else 0)
    blocked = int((row.blocked or 0) if row else 0)

    if blocked > 0:
        ordre.statut = _STATUT_BLOQUE
    elif in_progress > 0:
        ordre.statut = "EN_COURS"
    elif total > 0 and done == total:
        ordre.statut = _STATUT_TERMINE
    elif total > 0:
        ordre.statut = "ASSIGNÉ"

    await db.commit()


@router.put(
    "/interventions/{intervention_id}/status", response_model=InterventionResponse,
responses={400: {"description": "Intervention must be approved by ChefTech before starting; Declined intervention cannot be started"}, 404: {"description": "Intervention not found"}})
async def update_intervention_status(
    intervention_id: int,
    data: InterventionStatusUpdate,
    current_user: Annotated[Utilisateurs, Depends(verify_technicien)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    intervention = await db.scalar(
        select(OrdresIntervention).where(
            and_(OrdresIntervention.id == intervention_id, OrdresIntervention.technician_id == current_user.id)
        )
    )
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")

    _validate_status_transition(intervention, data)

    now = datetime.now(timezone.utc)
    old_status = intervention.statut

    intervention.statut = data.statut
    if data.rapport is not None:
        intervention.rapport = data.rapport
    if data.actual_failure_type is not None:
        intervention.actual_failure_type = data.actual_failure_type
    if data.ml_prediction_matched is not None:
        intervention.ml_prediction_matched = data.ml_prediction_matched

    _apply_intervention_dates(intervention, data, now)

    await db.commit()
    await db.refresh(intervention)

    # P7.6 feedback — non-fatal
    if data.statut in (_STATUT_TERMINE, "VALIDATED") and intervention.legacy_parts_text:
        try:
            from modules.ml.services.p7_feedback import record_p7_feedback
            await record_p7_feedback(intervention.id, db)
        except Exception as _fb_err:
            logger.debug(f"[P7-feedback] non-fatal error: {_fb_err}")

    if data.statut != old_status:
        await _notify_status_change(db, current_user, intervention, old_status, data.statut)

    await _propagate_wo_status(db, intervention.ordre_travail_id)

    return intervention


@router.post(
    "/interventions/request", response_model=InterventionResponse, status_code=201, 
responses={400: {"description": "Intervention cannot be requested in its current status"}})
async def request_intervention(
    payload: InterventionRequestPayload,
    current_user: Annotated[Utilisateurs, Depends(verify_technicien)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    now = datetime.now(timezone.utc)

    intervention = None
    if payload.ordre_travail_id:
        intervention = await db.scalar(
            select(OrdresIntervention).where(
                and_(
                    OrdresIntervention.ordre_travail_id == payload.ordre_travail_id,
                    OrdresIntervention.technician_id == current_user.id,
                )
            )
        )

    if not intervention:
        intervention = OrdresIntervention(
            date_intervention=now,
            ordre_travail_id=payload.ordre_travail_id,
            planning_tache_id=payload.planning_tache_id,
            technician_id=current_user.id,
            requested_by=current_user.id,
            statut="PENDING_APPROVAL",
            requested_at=now,
            machine_id=payload.machine_id,
            problem_description=payload.problem_description,
            priority=payload.priority,
            estimated_duration_minutes=payload.estimated_duration_minutes,
            required_materials=payload.required_materials,
            machine_category=payload.machine_category,
            symptoms=payload.symptoms,
            problem_start_time=payload.problem_start_time,
            frequency=payload.frequency,
            operating_state=payload.operating_state,
            temperature=payload.temperature,
            impact=payload.impact,
            estimated_loss=payload.estimated_loss,
            similar_issue_before=payload.similar_issue_before,
        )
        db.add(intervention)
        await db.flush()

    if payload.planning_tache_id:
        tache = await db.scalar(
            select(PlanningTaches).where(
                PlanningTaches.id == payload.planning_tache_id
            )
        )
        if tache and tache.statut == "DRAFT":
            tache.statut = "IN_PROGRESS"
    else:
        if intervention.statut not in {"EN_ATTENTE", "PENDING_APPROVAL", "DECLINED"}:
            raise HTTPException(
                status_code=400,
                detail="Intervention cannot be requested in its current status",
            )
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
        intervention.machine_category = payload.machine_category
        intervention.symptoms = payload.symptoms
        intervention.problem_start_time = payload.problem_start_time
        intervention.frequency = payload.frequency
        intervention.operating_state = payload.operating_state
        intervention.temperature = payload.temperature
        intervention.impact = payload.impact
        intervention.estimated_loss = payload.estimated_loss
        intervention.similar_issue_before = payload.similar_issue_before

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
    tech_payload = {
        "id": current_user.id,
        "nom": current_user.nom,
        "email": current_user.email,
    }

    try:
        rmq = await get_rabbitmq()
        await rmq.publish_intervention_event(
            ROUTING_KEY_INT_REQUESTED,
            {
                "intervention": int_payload,
                "requested_by": tech_payload,
            },
        )
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
            notify_intervention_requested.delay(
                int_payload, tech_payload, cheftech_recipients
            )
    except Exception as task_err:
        logger.warning(f"Celery task dispatch failed (non-blocking): {task_err}")

    return intervention
