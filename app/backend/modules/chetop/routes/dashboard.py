import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs
from models.ordres_intervention import Ordres_intervention
from models.machines import Machines
from ..schemas import DashboardStats
from typing import Annotated

router = APIRouter(prefix="/api/v1/chetop", tags=["chetop"])
logger = logging.getLogger(__name__)


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    _current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """CHETOP Dashboard - Updated for Intervention Requests"""
    try:
        # Request statistics
        total_requests_result = await db.execute(
            select(func.count(Ordres_intervention.id))
        )
        total_requests = total_requests_result.scalar_one()

        pending_result = await db.execute(
            select(func.count(Ordres_intervention.id)).where(
                Ordres_intervention.statut == "EN_ATTENTE"
            )
        )
        requests_pending = pending_result.scalar_one()

        approved_result = await db.execute(
            select(func.count(Ordres_intervention.id)).where(
                Ordres_intervention.statut == "ACCEPTED"
            )
        )
        requests_approved = approved_result.scalar_one()

        rejected_result = await db.execute(
            select(func.count(Ordres_intervention.id)).where(
                Ordres_intervention.statut == "REJECTED"
            )
        )
        requests_rejected = rejected_result.scalar_one()

        # Machine statistics
        total_machines_result = await db.execute(select(func.count(Machines.id)))
        total_machines = total_machines_result.scalar_one()

        machines_en_maintenance_result = await db.execute(
            select(func.count(Machines.id)).where(Machines.statut == "en_maintenance")
        )
        machines_en_maintenance = machines_en_maintenance_result.scalar_one()

        machines_hors_service_result = await db.execute(
            select(func.count(Machines.id)).where(Machines.statut == "hors_service")
        )
        machines_hors_service = machines_hors_service_result.scalar_one()

        return DashboardStats(
            total_requests=total_requests,
            requests_pending=requests_pending,
            requests_approved=requests_approved,
            requests_rejected=requests_rejected,
            total_machines=total_machines,
            machines_en_maintenance=machines_en_maintenance,
            machines_hors_service=machines_hors_service,
        )
    except Exception as e:
        logger.exception(f"Error getting dashboard stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
