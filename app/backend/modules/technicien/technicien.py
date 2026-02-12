from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.ordres_intervention import Ordres_intervention
from models.ordres_travail import Ordres_travail
from models.utilisateurs import Utilisateurs
from modules.auth.auth import get_current_user

router = APIRouter(prefix="/api/v1/technicien", tags=["technicien"])


class InterventionResponse(BaseModel):
    id: int
    ordre_travail_id: int
    statut: str
    date_intervention: datetime
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    rapport: Optional[str] = None

    class Config:
        from_attributes = True


class InterventionStatusUpdate(BaseModel):
    statut: str
    rapport: Optional[str] = None


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
    return list(result.scalars().all())


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

    valid_statuses = {"EN_ATTENTE", "EN_COURS", "TERMINÉ", "BLOQUÉ"}
    if data.statut not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid statut. Allowed: {sorted(valid_statuses)}")

    now = datetime.utcnow()

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
