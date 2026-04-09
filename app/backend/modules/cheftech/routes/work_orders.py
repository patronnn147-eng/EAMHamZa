import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from schemas.pagination import PaginatedResponse

from core.database import get_db
from core.rabbitmq import (
    get_rabbitmq,
    ROUTING_KEY_WO_ASSIGNED,
)
from models.utilisateurs import Utilisateurs
from models.ordres_intervention import Ordres_intervention
from models.ordres_travail import Ordres_travail
from models.machines import Machines
from services.notifications import NotificationsService
from tasks.work_order_events import notify_work_order_assigned
from ..schemas import WorkOrderResponse, WorkOrderAssignRequest
from ..dependencies import verify_cheftech, verify_cheftech_or_admin

router = APIRouter(prefix="/api/v1/cheftech", tags=["cheftech"])
logger = logging.getLogger(__name__)


@router.get("/ordres-travail", response_model=PaginatedResponse[WorkOrderResponse])
async def get_work_orders(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    statut: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    _current_user: Utilisateurs = Depends(verify_cheftech),
):
    """Get work orders with optional status filter"""
    try:
        skip = (page - 1) * size
        
        # Count total
        count_query = select(func.count(Ordres_travail.id))
        if statut:
            count_query = count_query.where(Ordres_travail.statut == statut)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = select(Ordres_travail)

        # Apply filter
        if statut:
            query = query.where(Ordres_travail.statut == statut)

        query = query.options(
            selectinload(Ordres_travail.machine),
            selectinload(Ordres_travail.utilisateur),
        )
        query = query.order_by(Ordres_travail.created_at.desc()).offset(skip).limit(size)
        result = await db.execute(query)

        work_orders = [
            WorkOrderResponse(
                id=ordre.id,
                titre=ordre.titre,
                description=ordre.description,
                statut=ordre.statut,
                priorite=ordre.priorite,
                machine_id=ordre.machine_id,
                utilisateur_id=ordre.utilisateur_id,
                date_echeance=ordre.date_echeance,
                created_at=ordre.created_at,
                updated_at=ordre.updated_at
            )
            for ordre in result.scalars()
        ]

        return PaginatedResponse.create(
            items=work_orders,
            total=total,
            page=page,
            size=size
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/ordres-travail/{ordre_id}/assign")
async def assign_work_order(
    ordre_id: int,
    data: WorkOrderAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(verify_cheftech_or_admin),
):
    if not data.technicien_ids:
        raise HTTPException(status_code=400, detail="technicien_ids is required")

    ordre = await db.scalar(select(Ordres_travail).where(Ordres_travail.id == ordre_id))
    if not ordre:
        raise HTTPException(status_code=404, detail="Work order not found")

    machine_ids = (
        [mid for mid in (data.machine_ids or []) if isinstance(mid, int)]
        if data.machine_ids is not None
        else []
    )
    if not machine_ids:
        machine_ids = [ordre.machine_id]

    machine_ids = sorted(set(machine_ids))

    machine_result = await db.execute(select(Machines.id).where(Machines.id.in_(machine_ids)))
    found_machine_ids = set(machine_result.scalars().all())
    missing_machines = [mid for mid in machine_ids if mid not in found_machine_ids]
    if missing_machines:
        raise HTTPException(status_code=400, detail=f"Invalid machine ids: {missing_machines}")

    tech_result = await db.execute(
        select(Utilisateurs.id).where(
            and_(
                Utilisateurs.id.in_(data.technicien_ids),
                cast(Utilisateurs.role, String) == "TECHNICIEN",
            )
        )
    )
    found_ids = set(tech_result.scalars().all())
    missing = [tid for tid in data.technicien_ids if tid not in found_ids]
    if missing:
        raise HTTPException(status_code=400, detail=f"Invalid technician ids: {missing}")

    now = datetime.now(timezone.utc)
    assigned_order_ids: List[int] = []

    for idx, machine_id in enumerate(machine_ids):
        if idx == 0:
            target_ordre = ordre
            target_ordre.machine_id = machine_id
        else:
            target_ordre = Ordres_travail(
                titre=ordre.titre,
                description=ordre.description,
                priorite=ordre.priorite,
                machine_id=machine_id,
                utilisateur_id=ordre.utilisateur_id,
                date_echeance=ordre.date_echeance,
                statut=ordre.statut,
                created_by=ordre.created_by,
                validated_by=ordre.validated_by,
                date_validation=ordre.date_validation,
                estimated_duration=ordre.estimated_duration,
            )
            db.add(target_ordre)
            await db.flush()

        target_ordre.statut = "ASSIGNÉ"
        target_ordre.validated_by = current_user.id
        target_ordre.date_validation = target_ordre.date_validation or now
        if data.estimated_completion_date:
            target_ordre.date_echeance = data.estimated_completion_date

        for technicien_id in data.technicien_ids:
            existing = await db.scalar(
                select(Ordres_intervention).where(
                    and_(
                        Ordres_intervention.ordre_travail_id == target_ordre.id,
                        Ordres_intervention.technicien_id == technicien_id,
                    )
                )
            )
            if existing:
                continue
            db.add(
                Ordres_intervention(
                    date_intervention=now,
                    ordre_travail_id=target_ordre.id,
                    technicien_id=technicien_id,
                    statut="EN_ATTENTE",
                )
            )

        assigned_order_ids.append(target_ordre.id)

    await db.commit()

    notif_service = NotificationsService(db)
    notif_now = datetime.now(timezone.utc)

    # Notify technicians
    for tech_id in sorted(set(data.technicien_ids)):
        await notif_service.create(
            {
                "utilisateur_id": tech_id,
                "titre": "Work Order Assigned",
                "priorite": ordre.priorite,
                "type": "WORK_ORDER_ASSIGNED",
                "message": f"Work order #{assigned_order_ids[0]} assigned to you.",
                "date_envoi": notif_now,
                "lu": False,
                "created_at": notif_now,
            }
        )

    # Notify ChefOp (creator)
    if getattr(ordre, "created_by", None):
        await notif_service.create(
            {
                "utilisateur_id": ordre.created_by,
                "titre": "Work Order Assigned",
                "priorite": ordre.priorite,
                "type": "WORK_ORDER_ASSIGNED",
                "message": f"Work order #{assigned_order_ids[0]} has been assigned by ChefTech.",
                "date_envoi": notif_now,
                "lu": False,
                "created_at": notif_now,
            }
        )

    # RabbitMQ event + Celery email for work order assignment
    wo_payload = {
        "id": ordre.id,
        "titre": ordre.titre,
        "description": ordre.description,
        "priorite": ordre.priorite,
        "statut": ordre.statut,
    }
    assigner_payload = {"id": current_user.id, "nom": current_user.nom, "email": current_user.email}

    try:
        rmq = await get_rabbitmq()
        await rmq.publish_work_order_event(ROUTING_KEY_WO_ASSIGNED, {
            "work_order": wo_payload,
            "assigned_by": assigner_payload,
            "technicien_ids": data.technicien_ids,
            "assigned_order_ids": assigned_order_ids,
        })
    except Exception as rmq_err:
        logger.warning(f"RabbitMQ publish failed (non-blocking): {rmq_err}")

    try:
        tech_result_notif = await db.execute(
            select(Utilisateurs).where(Utilisateurs.id.in_(data.technicien_ids))
        )
        tech_recipients = [
            {"email": u.email, "nom": u.nom} for u in tech_result_notif.scalars().all()
        ]
        creator_recipient = None
        if getattr(ordre, "created_by", None):
            creator_res = await db.execute(
                select(Utilisateurs).where(Utilisateurs.id == ordre.created_by)
            )
            creator_user = creator_res.scalar_one_or_none()
            if creator_user:
                creator_recipient = {"email": creator_user.email, "nom": creator_user.nom}

        if tech_recipients:
            notify_work_order_assigned.delay(
                wo_payload, assigner_payload, tech_recipients, creator_recipient
            )
    except Exception as task_err:
        logger.warning(f"Celery task dispatch failed (non-blocking): {task_err}")

    return {
        "message": "Work order assigned",
        "ordre_id": ordre_id,
        "assigned_order_ids": assigned_order_ids,
        "technicien_ids": data.technicien_ids,
        "machine_ids": machine_ids,
    }
