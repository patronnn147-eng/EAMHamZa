from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.pagination import PaginatedResponse

from core.database import get_db
from models.utilisateurs import Utilisateurs
from models.ordres_travail import OrdresTravail, OrdreStatut
from ..schemas import WorkOrderResponse
from ..dependencies import verify_cheftech

router = APIRouter(prefix="/api/v1/cheftech", tags=["cheftech"])


@router.get("/ordres-travail", response_model=PaginatedResponse[WorkOrderResponse], responses={400: {"description": "Bad Request"}})
async def get_work_orders(
    *, page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 10,
    statut: Annotated[Optional[str], Query()] = None,
    priorite: Annotated[Optional[str], Query()] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[Utilisateurs, Depends(verify_cheftech)],
):
    skip = (page - 1) * size

    count_query = select(func.count(OrdresTravail.id)).where(
        OrdresTravail.archived_at.is_(None)
    )
    query = select(OrdresTravail).where(OrdresTravail.archived_at.is_(None))

    if statut:
        try:
            statut_enum = OrdreStatut(statut)
            count_query = count_query.where(OrdresTravail.statut == statut_enum)
            query = query.where(OrdresTravail.statut == statut_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Statut invalide: {statut}")

    if priorite:
        count_query = count_query.where(OrdresTravail.priorite == priorite)
        query = query.where(OrdresTravail.priorite == priorite)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(OrdresTravail.created_at.desc()).offset(skip).limit(size)
    # nosemgrep: python.fastapi.db.generic-sql-fastapi -- `query` is a SQLAlchemy
    # Core select() where `statut`/`priorite` are bound via ORM == (statut is coerced
    # through the OrdreStatut enum first); no raw SQL or string interpolation.
    result = await db.execute(query)
    items = [WorkOrderResponse.model_validate(ot) for ot in result.scalars()]

    return PaginatedResponse.create(items=items, total=total, page=page, size=size)
