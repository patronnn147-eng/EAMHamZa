from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import get_db
from models.ordres_intervention import Ordres_intervention
from models.ordres_travail import Ordres_travail
from models.utilisateurs import Utilisateurs, UserRole
from core.auth import get_current_user

# Auto-discovered by main.py because of "admin_router" variable
admin_router = APIRouter(prefix="/api/v1/admin/analytics", tags=["admin_analytics"])


def verify_admin(current_user: Utilisateurs = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403, detail="Accès réservé aux administrateurs."
        )
    return current_user


@admin_router.get("/dashboard")
async def get_admin_analytics_dashboard(
    current_user: Utilisateurs = Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns system-wide analytics, technician performance, and request trends for Admin.
    """
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

    completed_wos = [wo for wo in all_wos if wo.statut == "TERMINE"]

    # 1. High-Level KPIs
    total_completed = len(completed_wos)

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

    approved_ints = [i for i in all_ints if i.statut == "APPROUVE"]
    requests_validated = len(approved_ints)

    # 2. Technician Performance
    tech_stats = {}
    for wo in completed_wos:
        tid = wo.utilisateur_id or "Unassigned"
        if tid not in tech_stats:
            tech_stats[tid] = {"completed": 0, "total_duration": 0}

        tech_stats[tid]["completed"] += 1
        if wo.date_debut and wo.date_fin:
            tech_stats[tid]["total_duration"] += int(
                (wo.date_fin - wo.date_debut).total_seconds() / 60
            )

    tech_performance = []
    for tid, stats in tech_stats.items():
        avg = (
            round(stats["total_duration"] / stats["completed"], 1)
            if stats["completed"] > 0
            else 0
        )
        tech_performance.append(
            {
                "technician_id": tid,
                "completed": stats["completed"],
                "avg_duration": avg,
            }
        )

    # Sort technicians by completed amount
    tech_performance.sort(key=lambda x: x["completed"], reverse=True)

    # 3. Request Trends
    accepted_ints = len(approved_ints)
    rejected_ints = sum(1 for i in all_ints if i.statut == "REJETE")
    pending_ints = sum(1 for i in all_ints if i.statut == "EN_ATTENTE")

    # Simple trend by day for interventions
    req_trends = {}
    for i in all_ints:
        if i.date_intervention:
            day_str = i.date_intervention.strftime("%Y-%m-%d")
            if day_str not in req_trends:
                req_trends[day_str] = {"accepted": 0, "rejected": 0, "pending": 0}

            if i.statut == "APPROUVE":
                req_trends[day_str]["accepted"] += 1
            elif i.statut == "REJETE":
                req_trends[day_str]["rejected"] += 1
            elif i.statut == "EN_ATTENTE":
                req_trends[day_str]["pending"] += 1

    trend_chart = [
        {"date": date_str, **counts} for date_str, counts in sorted(req_trends.items())
    ]

    return {
        "kpis": {
            "total_completed": total_completed,
            "avg_duration_minutes": avg_duration,
            "requests_validated": requests_validated,
            "failures_by_type": failure_counts,
        },
        "technician_performance": tech_performance,
        "request_trends": {
            "total_accepted": accepted_ints,
            "total_rejected": rejected_ints,
            "total_pending": pending_ints,
            "daily_trends": trend_chart,
        },
    }


@admin_router.get("/export")
async def export_admin_analytics(
    current_user: Utilisateurs = Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Exports aggregate analytics data as a CSV file.
    """
    w_result = await db.execute(
        select(Ordres_travail)
        .options(selectinload(Ordres_travail.machine))
        .options(selectinload(Ordres_travail.utilisateur))
    )
    all_wos = list(w_result.scalars().all())

    # Generate CSV content
    csv_content = "ID,Titre,Statut,Priorite,Date Echeance,Date Fin,Duree (min),Type Panne,Feedback ChefTech\n"

    for wo in all_wos:
        duration = ""
        if wo.date_debut and wo.date_fin:
            duration = str(int((wo.date_fin - wo.date_debut).total_seconds() / 60))

        date_echeance = (
            wo.date_echeance.strftime("%Y-%m-%d %H:%M:%S") if wo.date_echeance else ""
        )
        date_fin = wo.date_fin.strftime("%Y-%m-%d %H:%M:%S") if wo.date_fin else ""
        ft = wo.failure_type or ""
        fb = wo.cheftech_feedback or ""
        # Escape commas and quotes for CSV
        clean_titre = wo.titre.replace('"', '""')
        clean_fb = fb.replace('"', '""')
        titre = f'"{clean_titre}"' if '"' in wo.titre or "," in wo.titre else wo.titre
        fb = f'"{clean_fb}"' if '"' in fb or "," in fb else fb

        csv_content += f"{wo.id},{titre},{wo.statut},{wo.priorite},{date_echeance},{date_fin},{duration},{ft},{fb}\n"

    # Return as downloadable CSV
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=export_work_orders_{datetime.now().strftime('%Y%m%d%H%M')}.csv"
        },
    )
