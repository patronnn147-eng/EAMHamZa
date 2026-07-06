from typing import Optional, Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.pagination import PaginatedResponse

from core.database import get_db
from models.utilisateurs import Utilisateurs, UserRole
from models.machines import Machines
from ..schemas import MachineResponse, TechnicianResponse
from ..dependencies import verify_cheftech

router = APIRouter(prefix="/api/v1/cheftech", tags=["cheftech"])

_INTERNAL_SERVER_ERROR_MSG = "Internal server error"


@router.get("/techniciens", response_model=PaginatedResponse[TechnicianResponse], responses={500: {"description": "Internal server error"}})
async def get_technicians(
    *, page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 10,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[Utilisateurs, Depends(verify_cheftech)],
):
    """Get all technicians"""
    try:
        skip = (page - 1) * size

        # Count total
        count_query = select(func.count(Utilisateurs.id)).where(
            Utilisateurs.role == UserRole.TECHNICIEN
        )
        # nosemgrep: python.fastapi.db.generic-sql-fastapi -- `count_query` is a
        # SQLAlchemy Core select() with a fixed enum comparison; no raw SQL/interpolation.
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = select(Utilisateurs).where(Utilisateurs.role == UserRole.TECHNICIEN)
        query = query.order_by(Utilisateurs.nom).offset(skip).limit(size)
        result = await db.execute(query)

        technicians = [
            TechnicianResponse(
                id=tech.id, nom=tech.nom, email=tech.email, role=tech.role
            )
            for tech in result.scalars()
        ]

        return PaginatedResponse.create(
            items=technicians, total=total, page=page, size=size
        )
    except Exception:
        raise HTTPException(status_code=500, detail=_INTERNAL_SERVER_ERROR_MSG)


@router.get("/machines", response_model=PaginatedResponse[MachineResponse], responses={500: {"description": "Internal server error"}})
async def get_machines(
    *, page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 10,
    statut: Annotated[Optional[str], Query(description="Filter by status")] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[Utilisateurs, Depends(verify_cheftech)],
):
    """Get machines with optional status filter"""
    try:
        skip = (page - 1) * size

        # Count total
        count_query = select(func.count(Machines.id))
        if statut:
            count_query = count_query.where(Machines.statut == statut)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = select(Machines)

        # Apply filter
        if statut:
            query = query.where(Machines.statut == statut)

        query = query.order_by(Machines.nom).offset(skip).limit(size)
        # nosemgrep: python.fastapi.db.generic-sql-fastapi -- `query` is a SQLAlchemy
        # Core select() with `statut` bound via ORM ==, never interpolated raw SQL.
        result = await db.execute(query)

        machines = [
            MachineResponse(
                id=machine.id,
                nom=machine.nom,
                emplacement=machine.emplacement,
                statut=machine.statut,
                type=machine.type,
                date_derniere_maintenance=machine.date_derniere_maintenance,
                date_prochaine_maintenance=machine.date_prochaine_maintenance,
                image_url=machine.image_url,
                created_at=machine.created_at,
            )
            for machine in result.scalars()
        ]

        return PaginatedResponse.create(
            items=machines, total=total, page=page, size=size
        )
    except Exception:
        raise HTTPException(status_code=500, detail=_INTERNAL_SERVER_ERROR_MSG)


@router.put("/machines/{machine_id}/status", responses={400: {"description": "Le champ 'statut' est requis"}, 404: {"description": "Machine non trouvée"}, 500: {"description": "Internal server error"}})
async def update_machine_status(
    machine_id: int,
    payload: dict,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[Utilisateurs, Depends(verify_cheftech)],
):
    """Update machine status"""
    statut = payload.get("statut")
    if not statut:
        raise HTTPException(status_code=400, detail="Le champ 'statut' est requis")
    try:
        machine = await db.scalar(select(Machines).where(Machines.id == machine_id))
        if not machine:
            raise HTTPException(status_code=404, detail="Machine non trouvée")

        valid_statuses = ["ACTIF", "INACTIF", "MAINTENANCE", "CRITIQUE", "HORS_SERVICE"]
        if statut not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Statut invalide. Valeurs valides: {valid_statuses}",
            )

        machine.statut = statut
        await db.commit()
        return {"message": "Statut de la machine mis à jour avec succès"}
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail=_INTERNAL_SERVER_ERROR_MSG)
