import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs
from models.ordres_intervention import Ordres_intervention
from models.machines import Machines
from ..schemas import DashboardStats

router = APIRouter(prefix="/api/v1/chetop", tags=["chetop"])
logger = logging.getLogger(__name__)


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    _current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """CHETOP Dashboard - Updated for Intervention Requests"""
    try:
        # Request statistics
        total_requests_result = await db.execute(
            select(Ordres_intervention).options(
                selectinload(Ordres_intervention.machine)
            )
        )
        total_requests = len(total_requests_result.scalars().all())

        pending_result = await db.execute(
            select(Ordres_intervention).where(
                Ordres_intervention.statut == "EN_ATTENTE"
            )
        )
        requests_pending = len(pending_result.scalars().all())

        approved_result = await db.execute(
            select(Ordres_intervention).where(Ordres_intervention.statut == "ACCEPTED")
        )
        requests_approved = len(approved_result.scalars().all())

        rejected_result = await db.execute(
            select(Ordres_intervention).where(Ordres_intervention.statut == "REJECTED")
        )
        requests_rejected = len(rejected_result.scalars().all())

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
            total_requests=total_requests,
            requests_pending=requests_pending,
            requests_approved=requests_approved,
            requests_rejected=requests_rejected,
            total_machines=total_machines,
            machines_en_maintenance=machines_en_maintenance,
            machines_hors_service=machines_hors_service,
        )
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
