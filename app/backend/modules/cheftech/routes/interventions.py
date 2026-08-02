import logging
from datetime import datetime, timezone
from typing import List, Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from schemas.pagination import PaginatedResponse

from core.database import get_db
from models.utilisateurs import Utilisateurs
from models.utilisateur_zones import UtilisateurZone
from models.ordres_intervention import OrdresIntervention
from models.ordres_travail import OrdresTravail
from models.machines import Machines
from ..schemas import InterventionResponse
from ..dependencies import verify_cheftech

router = APIRouter(prefix="/api/v1/cheftech", tags=["cheftech"])
logger = logging.getLogger(__name__)


@router.get("/interventions", response_model=PaginatedResponse[InterventionResponse], responses={500: {"description": "Internal server error"}})
async def get_interventions(
    *, page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 10,
    statut: Annotated[Optional[str], Query(description="Filter by status")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(verify_cheftech)],
):
    """Get all interventions (including approval workflow fields)"""
    try:
        skip = (page - 1) * size

        # Zone-scope: a CHEFTECH sees interventions for machines in any zone
        # they're assigned to (utilisateur_zones). Unassigned CHEFTECHs (no
        # zone rows yet) see everything — avoids breaking oversight before
        # zones are configured.
        zone_rows = await db.execute(
            select(UtilisateurZone.zone).where(
                UtilisateurZone.utilisateur_id == current_user.id
            )
        )
        my_zones = [z for (z,) in zone_rows.all()]
        zone_filter = (
            OrdresIntervention.machine_id.in_(
                select(Machines.id).where(Machines.zone.in_(my_zones))
            )
            if my_zones
            else None
        )

        count_query = select(func.count(OrdresIntervention.id)).where(
            OrdresIntervention.archived_at.is_(None)
        )
        if zone_filter is not None:
            count_query = count_query.where(zone_filter)
        if statut:
            count_query = count_query.where(OrdresIntervention.statut == statut)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = select(OrdresIntervention).where(
            OrdresIntervention.archived_at.is_(None)
        )
        if zone_filter is not None:
            query = query.where(zone_filter)
        if statut:
            query = query.where(OrdresIntervention.statut == statut)
        query = query.options(
            selectinload(OrdresIntervention.machine),
            selectinload(OrdresIntervention.technician),
            selectinload(OrdresIntervention.ordre_travail),
        )
        query = (
            query.order_by(OrdresIntervention.date_intervention.desc())
            .offset(skip)
            .limit(size)
        )
        # nosemgrep: python.fastapi.db.generic-sql-fastapi -- `query` is a SQLAlchemy
        # Core select() built from ORM columns/joins/filters above (statut is compared
        # via ==, never interpolated into raw SQL text).
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

        approver_ids = {i.approved_by for i in interventions if i.approved_by is not None}
        approver_id_to_nom: dict = {}
        if approver_ids:
            approver_rows = await db.execute(
                select(Utilisateurs.id, Utilisateurs.nom).where(Utilisateurs.id.in_(approver_ids))
            )
            approver_id_to_nom = {row.id: row.nom for row in approver_rows.all()}

        now = datetime.now(timezone.utc)
        enriched: List[dict] = []
        for i in interventions:
            due = due_map.get(i.ordre_travail_id)
            is_done = (i.statut or "") in {"TERMINÉ"} or i.date_fin is not None
            status = i.statut or ""
            eligible = status in {"APPROVED", "EN_COURS", "BLOQUÉ"}
            overdue = bool(eligible and due and (due < now) and (not is_done))

            enriched.append(
                {
                    **InterventionResponse.model_validate(i).model_dump(),
                    "work_order_due_date": due,
                    "is_overdue": overdue,
                    "technicien_nom": i.technician.nom if i.technician else None,
                    "approved_by_nom": approver_id_to_nom.get(i.approved_by) if i.approved_by else None,
                }
            )

        return PaginatedResponse.create(
            items=enriched, total=total, page=page, size=size
        )
    except Exception as e:
        logger.exception(f"Error loading interventions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
