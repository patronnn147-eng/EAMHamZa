from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.pagination import PaginatedResponse

from core.database import get_db
from models.utilisateurs import Utilisateurs
from models.ordres_travail import Ordres_travail, OrdreStatut
from ..schemas import WorkOrderResponse
from ..dependencies import verify_cheftech

router = APIRouter(prefix="/api/v1/cheftech", tags=["cheftech"])


@router.get("/ordres-travail", response_model=PaginatedResponse[WorkOrderResponse])
async def get_work_orders(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    statut: Optional[str] = Query(None),
    priorite: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _current_user: Utilisateurs = Depends(verify_cheftech),
):
    skip = (page - 1) * size

    count_query = select(func.count(Ordres_travail.id)).where(
        Ordres_travail.archived_at.is_(None)
    )
    query = select(Ordres_travail).where(Ordres_travail.archived_at.is_(None))

    if statut:
        try:
            statut_enum = OrdreStatut(statut)
            count_query = count_query.where(Ordres_travail.statut == statut_enum)
            query = query.where(Ordres_travail.statut == statut_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Statut invalide: {statut}")

    if priorite:
        count_query = count_query.where(Ordres_travail.priorite == priorite)
        query = query.where(Ordres_travail.priorite == priorite)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Ordres_travail.created_at.desc()).offset(skip).limit(size)
    result = await db.execute(query)
    items = [WorkOrderResponse.model_validate(ot) for ot in result.scalars()]

    return PaginatedResponse.create(items=items, total=total, page=page, size=size)
