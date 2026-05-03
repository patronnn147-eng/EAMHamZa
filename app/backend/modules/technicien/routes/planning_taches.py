from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import verify_technicien
from models.machines import Machines
from models.planning_taches import Planning_taches, TaskType
from models.plannings import PlanningStatut, Plannings

router = APIRouter(prefix="/api/v1/technicien", tags=["technicien"])


class TechnicianTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    titre: str
    description: str
    task_type: TaskType
    technician_id: int = Field(validation_alias="technicien_id")
    machine_id: int
    machine_nom: Optional[str] = None
    planning_id: int
    planning_identifiant: Optional[str] = None
    planning_statut: Optional[PlanningStatut] = None
    date_debut: datetime
    date_fin: datetime
    created_at: datetime


@router.get("/planning-taches", response_model=list[TechnicianTaskResponse])
async def get_my_planning_tasks(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(verify_technicien),
):
    result = await db.execute(
        select(Planning_taches).where(Planning_taches.technicien_id == current_user.id)
    )
    tasks = result.scalars().all()

    output = []
    for t in tasks:
        machine_result = await db.execute(select(Machines).where(Machines.id == t.machine_id))
        machine = machine_result.scalar_one_or_none()

        planning_result = await db.execute(select(Plannings).where(Plannings.id == t.planning_id))
        planning = planning_result.scalar_one_or_none()

        item = TechnicianTaskResponse.model_validate(t)
        item.machine_nom = machine.nom if machine else None
        item.planning_identifiant = planning.identifiant_planning if planning else None
        item.planning_statut = planning.planning_statut if planning else None
        output.append(item)

    return output
