import logging
from datetime import datetime, timezone
from typing import List, Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from schemas.pagination import PaginatedResponse

from core.database import get_db
from models.utilisateurs import Utilisateurs
from models.ordres_intervention import Ordres_intervention
from models.ordres_travail import Ordres_travail
from ..schemas import InterventionResponse
from ..dependencies import verify_cheftech

router = APIRouter(prefix="/api/v1/cheftech", tags=["cheftech"])
logger = logging.getLogger(__name__)


@router.get("/interventions", response_model=PaginatedResponse[InterventionResponse])
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

        # Count total - show interventions where current user is involved OR pending approval
        count_query = (
            select(func.count(Ordres_intervention.id))
            .where(Ordres_intervention.archived_at.is_(None))
            .outerjoin(
                Ordres_travail,
                Ordres_intervention.ordre_travail_id == Ordres_travail.id,
            )
            .where(
                or_(
                    Ordres_intervention.technician_id == current_user.id,
                    Ordres_travail.created_by == current_user.id,
                    Ordres_intervention.statut == "PENDING_APPROVAL",
                )
            )
        )
        if statut:
            count_query = count_query.where(Ordres_intervention.statut == statut)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = (
            select(Ordres_intervention)
            .where(Ordres_intervention.archived_at.is_(None))
            .outerjoin(
                Ordres_travail,
                Ordres_intervention.ordre_travail_id == Ordres_travail.id,
            )
            .where(
                or_(
                    Ordres_intervention.technician_id == current_user.id,
                    Ordres_travail.created_by == current_user.id,
                    Ordres_intervention.statut == "PENDING_APPROVAL",
                )
            )
        )
        if statut:
            query = query.where(Ordres_intervention.statut == statut)
        query = query.options(
            selectinload(Ordres_intervention.machine),
            selectinload(Ordres_intervention.technician),
            selectinload(Ordres_intervention.ordre_travail),
        )
        query = (
            query.order_by(Ordres_intervention.date_intervention.desc())
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
                select(Ordres_travail.id, Ordres_travail.date_echeance).where(
                    Ordres_travail.id.in_(ordre_ids)
                )
            )
            due_map = {row.id: row.date_echeance for row in ordres_res.all()}

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
                }
            )

        return PaginatedResponse.create(
            items=enriched, total=total, page=page, size=size
        )
    except Exception as e:
        logger.exception(f"Error loading interventions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
