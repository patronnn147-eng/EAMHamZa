import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs
from models.machines import Machines
from ..schemas import MachineResponse, MachineStatusUpdate

router = APIRouter(prefix="/api/v1/chetop", tags=["chetop"])
logger = logging.getLogger(__name__)


@router.get("/machines", response_model=List[MachineResponse])
async def get_machines(
    statut: Optional[str] = Query(None, description="Filter by status"),
    type: Optional[str] = Query(None, description="Filter by type"),
    emplacement: Optional[str] = Query(None, description="Filter by location"),
    _current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-CHETOP-006: Get machines with status overview"""
    try:
        query = select(Machines)

        if statut:
            query = query.where(Machines.statut == statut)
        if type:
            query = query.where(Machines.type == type)
        if emplacement:
            query = query.where(Machines.emplacement.ilike(f"%{emplacement}%"))

        query = query.order_by(Machines.nom)

        result = await db.execute(query)
        machines = result.scalars().all()

        return [MachineResponse(
            id=machine.id,
            nom=machine.nom,
            emplacement=machine.emplacement,
            type=machine.type,
            statut=machine.statut,
            created_at=machine.created_at
        ) for machine in machines]
    except Exception as e:
        logger.error(f"Error getting machines: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/machines/{machine_id}/status", response_model=MachineResponse)
async def update_machine_status(
    machine_id: int,
    data: MachineStatusUpdate,
    _current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """US-CHETOP-007: Update machine status"""
    try:
        # Get machine
        machine_result = await db.execute(
            select(Machines).where(Machines.id == machine_id)
        )
        machine = machine_result.scalar_one_or_none()
        if not machine:
            raise HTTPException(status_code=404, detail="Machine not found")
        
        # Update status
        machine.statut = data.statut
        
        await db.commit()
        await db.refresh(machine)
        
        return MachineResponse(
            id=machine.id,
            nom=machine.nom,
            emplacement=machine.emplacement,
            type=machine.type,
            statut=machine.statut,
            created_at=machine.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating machine status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
