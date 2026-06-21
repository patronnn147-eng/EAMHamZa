from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.utilisateurs import Utilisateurs, UserRole
from models.ordres_intervention import Ordres_intervention
from models.ordres_travail import Ordres_travail, OrdreStatut
from models.machines import Machines
from ..schemas import DashboardStats
from ..dependencies import verify_cheftech

router = APIRouter(prefix="/api/v1/cheftech", tags=["cheftech"])


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _current_user: Utilisateurs = Depends(verify_cheftech),
):
    """Get dashboard statistics for CHEFTECH"""
    try:
        # Intervention statistics
        total_interventions = await db.scalar(
            select(func.count(Ordres_intervention.id))
        )
        interventions_en_cours = await db.scalar(
            select(func.count(Ordres_intervention.id)).where(
                Ordres_intervention.statut == "EN_COURS"
            )
        )

        # Work order statistics
        total_ordres_travail = await db.scalar(select(func.count(Ordres_travail.id)))
        ordres_en_attente = await db.scalar(
            select(func.count(Ordres_travail.id)).where(
                Ordres_travail.statut == OrdreStatut.SUBMITTED
            )
        )
        ordres_en_cours = await db.scalar(
            select(func.count(Ordres_travail.id)).where(
                Ordres_travail.statut.in_(
                    [OrdreStatut.ASSIGNED, OrdreStatut.IN_PROGRESS]
                )
            )
        )

        # Technician statistics
        total_techniciens = await db.scalar(
            select(func.count(Utilisateurs.id)).where(
                Utilisateurs.role == UserRole.TECHNICIEN
            )
        )
        techniciens_disponibles = total_techniciens

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
            machines_critiques=machines_critiques or 0,
        )
    except Exception as e:
        print(f"Error in dashboard stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
