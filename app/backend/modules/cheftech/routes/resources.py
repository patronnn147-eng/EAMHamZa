from typing import Optional
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


@router.get("/techniciens", response_model=PaginatedResponse[TechnicianResponse])
async def get_technicians(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user: Utilisateurs = Depends(verify_cheftech),
):
    """Get all technicians"""
    try:
        skip = (page - 1) * size
        
        # Count total
        count_query = select(func.count(Utilisateurs.id)).where(Utilisateurs.role == UserRole.TECHNICIEN)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = select(Utilisateurs).where(Utilisateurs.role == UserRole.TECHNICIEN)
        query = query.order_by(Utilisateurs.nom).offset(skip).limit(size)
        result = await db.execute(query)

        technicians = [
            TechnicianResponse(
                id=tech.id,
                nom=tech.nom,
                email=tech.email,
                role=tech.role
            )
            for tech in result.scalars()
        ]

        return PaginatedResponse.create(
            items=technicians,
            total=total,
            page=page,
            size=size
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/machines", response_model=PaginatedResponse[MachineResponse])
async def get_machines(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    statut: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    _current_user: Utilisateurs = Depends(verify_cheftech),
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
                created_at=machine.created_at
            )
            for machine in result.scalars()
        ]

        return PaginatedResponse.create(
            items=machines,
            total=total,
            page=page,
            size=size
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/machines/{machine_id}/status")
async def update_machine_status(
    machine_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _current_user: Utilisateurs = Depends(verify_cheftech),
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
            raise HTTPException(status_code=400, detail=f"Statut invalide. Valeurs valides: {valid_statuses}")

        machine.statut = statut
        await db.commit()
        return {"message": "Statut de la machine mis à jour avec succès"}
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
