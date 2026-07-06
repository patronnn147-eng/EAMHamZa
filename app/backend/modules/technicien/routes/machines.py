import logging
from typing import List, Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.utilisateurs import Utilisateurs
from models.machines import Machines
from models.machine_telemetry import MachineTelemetry
from core.security import verify_technicien
from ..schemas import MachineResponse
from ..schemas_telemetry import MachineTelemetryResponse, MachineTelemetryLatest
from schemas.pagination import PaginatedResponse

router = APIRouter(prefix="/api/v1/technicien", tags=["technicien"])
logger = logging.getLogger(__name__)


@router.get("/machines", response_model=List[MachineResponse], responses={500: {"description": "Internal server error"}})
async def get_machines_list(
    *, statut: Annotated[Optional[str], Query()] = None,
    _current_user: Annotated[Utilisateurs, Depends(verify_technicien)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Return all machines for the technician's intervention request form."""
    try:
        query = select(Machines)
        if statut:
            query = query.where(Machines.statut == statut)
        query = query.order_by(Machines.nom)
        # nosemgrep: python.fastapi.db.generic-sql-fastapi -- `query` is a SQLAlchemy
        # Core select() where `statut` is bound via ORM ==, never interpolated raw SQL.
        result = await db.execute(query)
        machines = result.scalars().all()

        return [
            MachineResponse(
                id=m.id,
                nom=m.nom,
                emplacement=m.emplacement,
                type=m.type,
                statut=m.statut,
                created_at=m.created_at,
            )
            for m in machines
        ]
    except Exception as e:
        logger.exception(f"Error getting machines for technicien: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/machines/{machine_id}/telemetry",
    response_model=PaginatedResponse[MachineTelemetryResponse], responses={404: {"description": "Machine not found"}})
async def get_machine_telemetry(
    *, machine_id: int,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    current_user: Annotated[Utilisateurs, Depends(verify_technicien)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """TECHNICIEN: Get telemetry logs for a specific machine"""
    machine_result = await db.execute(select(Machines).where(Machines.id == machine_id))
    if not machine_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Machine not found")

    count_result = await db.execute(
        select(func.count(MachineTelemetry.id)).where(
            MachineTelemetry.machine_id == machine_id
        )
    )
    total = count_result.scalar() or 0

    skip = (page - 1) * size
    query = (
        select(MachineTelemetry)
        .where(MachineTelemetry.machine_id == machine_id)
        .order_by(desc(MachineTelemetry.recorded_at))
        .offset(skip)
        .limit(size)
    )

    result = await db.execute(query)
    records = result.scalars().all()

    items = [
        MachineTelemetryResponse(
            id=r.id,
            machine_id=r.machine_id,
            work_order_id=r.work_order_id,
            technician_id=r.technician_id,
            temperature=r.temperature,
            vibration=r.vibration,
            rpm=r.rpm,
            torque=r.torque,
            power=r.power,
            recorded_at=r.recorded_at,
            notes=r.notes,
            created_at=r.created_at,
        )
        for r in records
    ]

    return PaginatedResponse.create(items=items, total=total, page=page, size=size)


@router.get(
    "/machines/{machine_id}/telemetry/latest", response_model=MachineTelemetryLatest, 
responses={404: {"description": "Machine not found; No telemetry data found for this machine"}})
async def get_machine_latest_telemetry(
    machine_id: int,
    current_user: Annotated[Utilisateurs, Depends(verify_technicien)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """TECHNICIEN: Get latest telemetry reading for a machine"""
    machine_result = await db.execute(select(Machines).where(Machines.id == machine_id))
    machine = machine_result.scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    query = (
        select(MachineTelemetry)
        .where(MachineTelemetry.machine_id == machine_id)
        .order_by(desc(MachineTelemetry.recorded_at))
        .limit(1)
    )

    result = await db.execute(query)
    telemetry = result.scalar_one_or_none()

    if not telemetry:
        raise HTTPException(
            status_code=404, detail="No telemetry data found for this machine"
        )

    return MachineTelemetryLatest(
        machine_id=machine_id,
        machine_nom=machine.nom,
        temperature=telemetry.temperature,
        vibration=telemetry.vibration,
        rpm=telemetry.rpm,
        torque=telemetry.torque,
        power=telemetry.power,
        recorded_at=telemetry.recorded_at,
        work_order_id=telemetry.work_order_id,
    )
