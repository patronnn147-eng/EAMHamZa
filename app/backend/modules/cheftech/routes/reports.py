from datetime import datetime
from typing import Optional, List, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import get_db
from models.utilisateurs import Utilisateurs, UserRole
from models.ordres_travail import Ordres_travail, OrdreStatut
from models.machines import Machines
from ..schemas import CompletedWorkOrderItem, ChefTechFeedbackRequest
from ..dependencies import verify_cheftech_or_admin

router = APIRouter(prefix="/api/v1/cheftech", tags=["cheftech"])


@router.get("/completed-work-orders", response_model=List[CompletedWorkOrderItem])
async def get_completed_work_orders(
    *, page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 10,
    technician_id: Annotated[Optional[int], Query()] = None,
    machine_id: Annotated[Optional[int], Query()] = None,
    failure_type: Annotated[Optional[str], Query()] = None,
    date_from: Annotated[Optional[datetime], Query()] = None,
    date_to: Annotated[Optional[datetime], Query()] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[Utilisateurs, Depends(verify_cheftech_or_admin)],
):
    """Get all completed Work Orders enriched with technician and machine info."""
    skip = (page - 1) * size

    query = select(Ordres_travail).where(
        Ordres_travail.statut.in_(
            [OrdreStatut.COMPLETED, OrdreStatut.VALIDATED, OrdreStatut.CLOSED]
        )
    )
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
    # nosemgrep: python.fastapi.db.generic-sql-fastapi -- `query` is a SQLAlchemy
    # Core select() built from ORM column comparisons (technician_id/machine_id/
    # failure_type/date_from/date_to bound via ==/>=/<=), never raw SQL text.
    result = await db.execute(query)
    work_orders = list(result.scalars().all())

    # Enrich with technician and machine names
    user_ids = list({wo.utilisateur_id for wo in work_orders if wo.utilisateur_id})
    machine_ids = list({wo.machine_id for wo in work_orders if wo.machine_id})

    user_map: dict = {}
    machine_map: dict = {}

    if user_ids:
        users_res = await db.execute(
            select(Utilisateurs.id, Utilisateurs.nom, Utilisateurs.email).where(
                Utilisateurs.id.in_(user_ids)
            )
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
        items.append(
            CompletedWorkOrderItem(
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
            )
        )

    return items


@router.put("/work-orders/{ordre_id}/feedback", responses={400: {"description": "Le feedback ne peut être ajouté qu'aux ordres terminés"}, 403: {"description": "Accès refusé. ChefTech ou Admin requis."}, 404: {"description": "Ordre de travail non trouvé"}})
async def add_cheftech_feedback(
    ordre_id: int,
    data: ChefTechFeedbackRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(verify_cheftech_or_admin)],
):
    """Add ChefTech feedback to a completed Work Order. Does not alter execution data."""
    if current_user.role not in [UserRole.CHEFTECH, UserRole.ADMIN]:
        raise HTTPException(
            status_code=403, detail="Accès refusé. ChefTech ou Admin requis."
        )

    ordre = await db.scalar(select(Ordres_travail).where(Ordres_travail.id == ordre_id))
    if not ordre:
        raise HTTPException(status_code=404, detail="Ordre de travail non trouvé")

    if ordre.statut not in (
        OrdreStatut.COMPLETED,
        OrdreStatut.VALIDATED,
        OrdreStatut.CLOSED,
    ):
        raise HTTPException(
            status_code=400,
            detail="Le feedback ne peut être ajouté qu'aux ordres terminés",
        )

    ordre.cheftech_feedback = data.feedback.strip()
    await db.commit()

    return {
        "status": "success",
        "ordre_id": ordre_id,
        "feedback": ordre.cheftech_feedback,
    }


@router.get("/reports/kpi")
async def get_kpi_report(
    *, date_from: Annotated[Optional[datetime], Query()] = None,
    date_to: Annotated[Optional[datetime], Query()] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[Utilisateurs, Depends(verify_cheftech_or_admin)],
):
    """KPI summary for completed Work Orders. Available to ChefTech and Admin."""
    base_query = select(Ordres_travail).where(
        Ordres_travail.statut.in_(
            [OrdreStatut.COMPLETED, OrdreStatut.VALIDATED, OrdreStatut.CLOSED]
        )
    )
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
        "feedback_coverage_pct": round(
            (feedback_count / total * 100) if total else 0, 1
        ),
    }


@router.get("/analytics/dashboard")
async def get_cheftech_analytics_dashboard(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[Utilisateurs, Depends(verify_cheftech_or_admin)],
):
    """
    Returns analytics and PDCA metrics for the ChefTech dashboard.
    For simplicity in this MVP, we query all work orders and interventions
    to compute the PDCA stages and performance trends.
    """
    from models.ordres_intervention import Ordres_intervention

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
        .options(selectinload(Ordres_intervention.technician))
    )
    all_ints = list(i_result.scalars().all())

    # Metrics computation
    total_assigned = len(all_wos)
    completed_wos = [
        wo
        for wo in all_wos
        if wo.statut
        in (OrdreStatut.COMPLETED, OrdreStatut.VALIDATED, OrdreStatut.CLOSED)
    ]
    pending_wos = [
        wo
        for wo in all_wos
        if wo.statut in (OrdreStatut.SUBMITTED, OrdreStatut.APPROVED)
    ]
    in_progress_wos = [
        wo
        for wo in all_wos
        if wo.statut in (OrdreStatut.ASSIGNED, OrdreStatut.IN_PROGRESS)
    ]

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
    pdca_plan = sum(1 for i in all_ints if i.statut == "EN_ATTENTE")
    pdca_do = len(pending_wos) + len(in_progress_wos)
    pdca_check = len(completed_wos)
    pdca_act = sum(1 for wo in completed_wos if wo.cheftech_feedback)

    # Trend: Completions per day
    trend_dict = {}
    for wo in completed_wos:
        if wo.date_fin:
            day_str = wo.date_fin.strftime("%Y-%m-%d")
            trend_dict[day_str] = trend_dict.get(day_str, 0) + 1

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
            "late_wos": sum(
                1
                for wo in completed_wos
                if wo.date_fin and wo.date_echeance and wo.date_fin > wo.date_echeance
            ),
            "top_failure": max(failure_counts, key=failure_counts.get)
            if failure_counts
            else "N/A",
        },
    }
