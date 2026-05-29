from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from core.database import get_db
from core.security import get_current_user
from models.utilisateurs import Utilisateurs
from models.plannings import Plannings, PlanningStatut
from models.planning_taches import Planning_taches
from models.machines import Machines
from services.notifications import NotificationsService
from tasks.planning_tache_emails import send_task_assignment_email
from .schemas import (
    PlanningTacheCreate,
    PlanningTacheUpdate,
    PlanningTacheResponse,
    PlanningTacheListResponse,
    PlanningTachesSubmitRequest,
)

router = APIRouter(prefix="/api/v1/plannings/{planning_id}/taches", tags=["planning-taches"])
all_taches_router = APIRouter(prefix="/api/v1/plannings", tags=["planning-taches"])


async def get_planning_or_404(planning_id: int, db: AsyncSession) -> Plannings:
    result = await db.execute(select(Plannings).where(Plannings.id == planning_id))
    planning = result.scalar_one_or_none()
    if not planning:
        raise HTTPException(status_code=404, detail="Planning not found")
    return planning


def validate_task_dates(planning: Plannings, date_debut: datetime, date_fin: datetime):
    if date_debut < planning.date_debut:
        raise HTTPException(
            status_code=400,
            detail=f"Task start date must be >= planning start date ({planning.date_debut})"
        )
    if date_fin > planning.date_fin:
        raise HTTPException(
            status_code=400,
            detail=f"Task end date must be <= planning end date ({planning.date_fin})"
        )


@router.get("", response_model=PlanningTacheListResponse)
async def list_tasks(
    planning_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """List all tasks for a planning."""
    result = await db.execute(select(Planning_taches).where(Planning_taches.archived_at.is_(None)).where(Planning_taches.planning_id == planning_id))
    tasks = result.scalars().all()
    return {"items": tasks, "total": len(tasks)}


@router.post("", response_model=list[PlanningTacheResponse])
async def create_tasks(
    planning_id: int,
    request: PlanningTachesSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Create tasks and submit planning for approval."""
    planning = await get_planning_or_404(planning_id, db)
    
    if planning.planning_statut != PlanningStatut.DRAFT:
        raise HTTPException(status_code=400, detail="Only DRAFT plannings can have tasks")
    
    created_tasks = []
    for task_data in request.tasks:
        validate_task_dates(planning, task_data.date_debut, task_data.date_fin)
        
        task = Planning_taches(
            planning_id=planning_id,
            titre=task_data.titre,
            description=task_data.description,
            technicien_id=task_data.technician_id,
            machine_id=task_data.machine_id,
            task_type=task_data.task_type,
            date_debut=task_data.date_debut,
            date_fin=task_data.date_fin,
            created_by=current_user.id,
        )
        db.add(task)
        created_tasks.append(task)
    
    await db.commit()
    for task in created_tasks:
        await db.refresh(task)

    # Send bell notification + email to each assigned technician
    for task in created_tasks:
        tech_result = await db.execute(select(Utilisateurs).where(Utilisateurs.id == task.technicien_id))
        technician = tech_result.scalar_one_or_none()
        machine_result = await db.execute(select(Machines).where(Machines.id == task.machine_id))
        machine = machine_result.scalar_one_or_none()
        if technician:
            await NotificationsService(db).create({
                "utilisateur_id": technician.id,
                "titre": "Nouvelle tâche de planning assignée",
                "priorite": "HAUTE",
                "type": "PLANNING_ASSIGNMENT",
                "message": (
                    f"Tâche « {task.titre} » — "
                    f"{machine.nom if machine else ''} — "
                    f"Planning {planning.identifiant_planning}"
                ),
                "date_envoi": datetime.now(),
                "lu": False,
            })
            send_task_assignment_email.delay(
                technician={"id": technician.id, "nom": technician.nom, "email": technician.email},
                task={
                    "titre": task.titre,
                    "task_type": task.task_type.value,
                    "date_debut": str(task.date_debut),
                    "date_fin": str(task.date_fin),
                },
                machine_name=machine.nom if machine else str(task.machine_id),
                planning_identifiant=planning.identifiant_planning,
            )

    if request.submit:
        planning.planning_statut = PlanningStatut.SUBMITTED
        await db.commit()
    
    return created_tasks


@router.put("/{task_id}", response_model=PlanningTacheResponse)
async def update_task(
    planning_id: int,
    task_id: int,
    request: PlanningTacheUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Update a task."""
    planning = await get_planning_or_404(planning_id, db)
    
    if planning.planning_statut != PlanningStatut.DRAFT:
        raise HTTPException(status_code=400, detail="Only DRAFT plannings can be modified")
    
    result = await db.execute(
        select(Planning_taches).where(
            Planning_taches.id == task_id,
            Planning_taches.planning_id == planning_id
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if request.titre is not None:
        task.titre = request.titre
    if request.description is not None:
        task.description = request.description
    if request.technician_id is not None:
        task.technicien_id = request.technician_id
    if request.machine_id is not None:
        task.machine_id = request.machine_id
    if request.task_type is not None:
        task.task_type = request.task_type
    if request.date_debut is not None:
        task.date_debut = request.date_debut
    if request.date_fin is not None:
        task.date_fin = request.date_fin
    
    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}")
async def delete_task(
    planning_id: int,
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """Delete a task."""
    planning = await get_planning_or_404(planning_id, db)
    
    if planning.planning_statut != PlanningStatut.DRAFT:
        raise HTTPException(status_code=400, detail="Only DRAFT plannings can be modified")
    
    result = await db.execute(
        select(Planning_taches).where(
            Planning_taches.id == task_id,
            Planning_taches.planning_id == planning_id
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    await db.delete(task)
    await db.commit()
    return {"message": "Task deleted"}


@all_taches_router.get("/all-with-taches", response_model=list[dict])
async def list_plannings_with_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """List all plannings with their task counts."""
    tasks_subquery = (
        select(
            Planning_taches.planning_id,
            func.count(Planning_taches.id).label('task_count')
        )
        .where(Planning_taches.archived_at.is_(None))
        .group_by(Planning_taches.planning_id)
        .subquery()
    )

    result = await db.execute(
        select(
            Plannings.id,
            Plannings.identifiant_planning,
            Plannings.date_debut,
            Plannings.date_fin,
            Plannings.planning_statut,
            func.coalesce(tasks_subquery.c.task_count, 0).label('task_count')
        )
        .outerjoin(tasks_subquery, Plannings.id == tasks_subquery.c.planning_id)
        .where(Plannings.archived_at.is_(None))
        .order_by(Plannings.date_debut.desc())
    )
    rows = result.all()
    
    return [
        {
            "id": row[0],
            "identifiant_planning": row[1],
            "date_debut": row[2],
            "date_fin": row[3],
            "planning_statut": row[4],
            "task_count": row[5],
        }
        for row in rows
    ]