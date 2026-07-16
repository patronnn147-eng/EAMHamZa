from typing import List, Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.utilisateurs import Utilisateurs, UserRole
from models.OrdresIntervention import OrdresIntervention
from models.OrdresTravail import OrdresTravail, OrdreStatut
from models.machines import Machines
from ..schemas import DashboardStats, DistributionSlice, InterventionDistributions
from ..dependencies import verify_cheftech

router = APIRouter(prefix="/api/v1/cheftech", tags=["cheftech"])

UNSPECIFIED = "Non spécifié"


async def _count_by_column(db: AsyncSession, column) -> List[DistributionSlice]:
    """Group-count a column across ALL rows (active + archived).

    Deliberately does NOT filter on archived_at: archived rows still exist in
    the table and should count towards distributions until the retention
    sweep (ArchiveService.purge_old) hard-deletes them, at which point they
    disappear from this count automatically. NULL values are bucketed under
    UNSPECIFIED rather than dropped.
    """
    result = await db.execute(
        select(column, func.count(OrdresIntervention.id)).group_by(column)
    )
    slices: dict[str, int] = {}
    for raw_value, count in result.all():
        name = raw_value if raw_value else UNSPECIFIED
        slices[name] = slices.get(name, 0) + count
    return [
        DistributionSlice(name=name, value=value)
        for name, value in sorted(slices.items(), key=lambda kv: -kv[1])
    ]


@router.get("/dashboard", response_model=DashboardStats, responses={500: {"description": "Internal server error"}})
async def get_dashboard_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[Utilisateurs, Depends(verify_cheftech)],
):
    """Get dashboard statistics for CHEFTECH"""
    try:
        # Intervention statistics
        total_interventions = await db.scalar(
            select(func.count(OrdresIntervention.id))
        )
        interventions_en_cours = await db.scalar(
            select(func.count(OrdresIntervention.id)).where(
                OrdresIntervention.statut == "EN_COURS"
            )
        )

        # Work order statistics
        total_OrdresTravail = await db.scalar(select(func.count(OrdresTravail.id)))
        ordres_en_attente = await db.scalar(
            select(func.count(OrdresTravail.id)).where(
                OrdresTravail.statut == OrdreStatut.SUBMITTED
            )
        )
        ordres_en_cours = await db.scalar(
            select(func.count(OrdresTravail.id)).where(
                OrdresTravail.statut.in_(
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
            total_OrdresTravail=total_OrdresTravail or 0,
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


@router.get("/dashboard/distributions", response_model=InterventionDistributions, responses={500: {"description": "Internal server error"}})
async def get_intervention_distributions(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[Utilisateurs, Depends(verify_cheftech)],
):
    """Intervention breakdowns (status / type / root cause / machine category)
    for the dashboard pie charts. Includes archived interventions — only rows
    purged by the retention sweep drop out.
    """
    try:
        return InterventionDistributions(
            by_status=await _count_by_column(db, OrdresIntervention.statut),
            by_type=await _count_by_column(db, OrdresIntervention.intervention_type),
            by_root_cause=await _count_by_column(
                db, OrdresIntervention.root_cause_category
            ),
            by_machine_category=await _count_by_column(
                db, OrdresIntervention.machine_category
            ),
        )
    except Exception as e:
        print(f"Error in dashboard distributions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
