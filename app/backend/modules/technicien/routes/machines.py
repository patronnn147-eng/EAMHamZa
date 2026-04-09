import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.utilisateurs import Utilisateurs
from models.machines import Machines
from core.security import verify_technicien
from ..schemas import MachineResponse

router = APIRouter(prefix="/api/v1/technicien", tags=["technicien"])
logger = logging.getLogger(__name__)


@router.get("/machines", response_model=List[MachineResponse])
async def get_machines_list(
    statut: Optional[str] = Query(None),
    _current_user: Utilisateurs = Depends(verify_technicien),
    db: AsyncSession = Depends(get_db),
):
    """Return all machines for the technician's intervention request form."""
    try:
        query = select(Machines)
        if statut:
            query = query.where(Machines.statut == statut)
        query = query.order_by(Machines.nom)
        result = await db.execute(query)
        machines = result.scalars().all()

        return [MachineResponse(
            id=m.id,
            nom=m.nom,
            emplacement=m.emplacement,
            type=m.type,
            statut=m.statut,
            created_at=m.created_at
        ) for m in machines]
    except Exception as e:
        logger.error(f"Error getting machines for technicien: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
