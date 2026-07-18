from typing import Optional, Annotated
from datetime import datetime, timezone
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from schemas.pagination import PaginatedResponse

from core.database import get_db
from core.auth import get_current_user
from core.rabbitmq import (
    get_rabbitmq,
    ROUTING_KEY_WO_CREATED,
)
from models.utilisateurs import Utilisateurs, UserRole
from models.ordres_intervention import OrdresIntervention
from models.ordres_travail import OrdresTravail
from models.machines import Machines
from services.inventory import InventoryReservationService, InsufficientStockError
from services.ml.recovery import PostMaintenanceRecoveryService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/itv-requests", tags=["admin-itv"])


class ItvRequestValidation(BaseModel):
    status: str  # APPROVED, REJECTED
    rejection_reason: Optional[str] = None
    technician_id: Optional[int] = None  # Optional technician to assign


class ItvRequestResponse(BaseModel):
    id: int
    machine_id: int
    machine_nom: Optional[str] = None
    priorite: str
    description: str
    statut: str
    requested_at: Optional[datetime] = None
    requested_by_nom: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("", response_model=PaginatedResponse[ItvRequestResponse], responses={403: {"description": "Only Admins can see these requests"}, 500: {"description": "Internal server error"}})
async def get_all_pending_requests(
    *, page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 10,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Admin: List all PENDING intervention requests"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403, detail="Only Admins can see these requests"
        )

    try:
        skip = (page - 1) * size

        # Count total - get PENDING_APPROVAL status
        count_query = (
            select(func.count(OrdresIntervention.id))
            .where(OrdresIntervention.archived_at.is_(None))
            .where(OrdresIntervention.statut == "PENDING_APPROVAL")
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = (
            select(
                OrdresIntervention,
                Machines.nom.label("machine_nom"),
                Utilisateurs.nom.label("requester_nom"),
            )
            .outerjoin(Machines, OrdresIntervention.machine_id == Machines.id)
            .outerjoin(
                Utilisateurs, OrdresIntervention.requested_by == Utilisateurs.id
            )
            .where(OrdresIntervention.statut == "PENDING_APPROVAL")
            .order_by(OrdresIntervention.requested_at.asc())
            .offset(skip)
            .limit(size)
        )

        result = await db.execute(query)
        rows = result.all()

        items = [
            ItvRequestResponse(
                id=itv.id,
                machine_id=itv.machine_id,
                machine_nom=machine_nom,
                priorite=itv.priority or "MOYENNE",
                description=itv.problem_description or "",
                statut=itv.statut,
                requested_at=itv.requested_at,
                requested_by_nom=requester_nom,
            )
            for itv, machine_nom, requester_nom in rows
        ]

        return PaginatedResponse.create(items=items, total=total, page=page, size=size)
    except Exception as e:
        logger.exception(f"Error fetching pending requests: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def _handle_itv_rejected(
    db: AsyncSession, itv_request: OrdresIntervention, rejection_reason: Optional[str]
) -> None:
    """Mark intervention as DECLINED and release any prior stock reservation."""
    itv_request.statut = "DECLINED"
    itv_request.rejection_reason = rejection_reason
    try:
        await InventoryReservationService(db).release_all(
            intervention_id=itv_request.id,
            reason="rejected",
            auto_commit=False,
        )
    except Exception as rls_exc:
        safe_exc = str(rls_exc).replace("\r", "").replace("\n", "")
        logger.warning(f"Release on reject failed for itv {itv_request.id}: {safe_exc}")


async def _handle_itv_approved(
    db: AsyncSession, itv_request: OrdresIntervention, current_user: Utilisateurs
) -> None:
    """Reserve stock, create Work Order, snapshot health, publish RabbitMQ event."""
    # Reserve stock — rollback + 409 on shortage
    try:
        await InventoryReservationService(db).try_reserve(
            intervention_id=itv_request.id, auto_commit=False
        )
        itv_request.parts_approved = True
    except InsufficientStockError as ise:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Stock insuffisant pour cette intervention",
                "missing": [
                    {
                        "piece_id": m.piece_id,
                        "piece_name": m.piece_name,
                        "requested": str(m.requested),
                        "available": str(m.available),
                        "deficit": str(m.deficit),
                    }
                    for m in ise.missing
                ],
            },
        )
    except Exception as rsv_exc:
        safe_exc = str(rsv_exc).replace("\r", "").replace("\n", "")
        logger.warning(f"Reservation soft-failure for itv {itv_request.id}: {safe_exc}")

    itv_request.statut = "APPROVED"

    # Create Work Order assigned to the ChefOp who requested
    new_wo = OrdresTravail(
        titre=f"Intervention #{itv_request.id}",
        description=itv_request.problem_description or "",
        priorite=itv_request.priority or "MOYENNE",
        machine_id=itv_request.machine_id,
        utilisateur_id=itv_request.requested_by,
        statut="ASSIGNED",
        date_echeance=itv_request.requested_at,
        created_by=current_user.id,
        validated_by=current_user.id,
        date_validation=datetime.now(timezone.utc),
        estimated_duration=itv_request.estimated_duration_minutes,
    )
    db.add(new_wo)
    await db.flush()
    itv_request.ordre_travail_id = new_wo.id

    # Update title with machine name
    machine_result = await db.execute(
        select(Machines.nom).where(Machines.id == itv_request.machine_id)
    )
    machine_nom = machine_result.scalar_one_or_none()
    if machine_nom:
        new_wo.titre = f"Intervention #{itv_request.id} - {machine_nom}"

    # Snapshot pre-maintenance health baseline (non-blocking)
    try:
        _score = await PostMaintenanceRecoveryService(db).snapshot_health(new_wo.machine_id)
        if _score is not None:
            new_wo.health_score_at_creation = _score
    except Exception as _rec_exc:
        logger.warning("Recovery baseline snapshot failed for WO %s: %s", new_wo.id, _rec_exc)

    # Publish WO-created event (non-blocking)
    try:
        rmq = await get_rabbitmq()
        await rmq.publish_work_order_event(
            ROUTING_KEY_WO_CREATED,
            {
                "work_order": {
                    "id": new_wo.id,
                    "titre": new_wo.titre,
                    "machine_id": new_wo.machine_id,
                    "priorite": new_wo.priorite,
                    "statut": new_wo.statut,
                },
                "created_by": {"id": current_user.id, "nom": current_user.nom},
            },
        )
    except Exception as rmq_err:
        logger.warning(f"RabbitMQ publish failed: {rmq_err}")


@router.patch("/{request_id}/validate", responses={400: {"description": "Only pending approval requests can be validated"}, 403: {"description": "Only Admins can validate requests"}, 404: {"description": "Request not found"}, 409: {"description": "Conflict"}, 500: {"description": "Internal server error"}})
async def validate_itv_request(
    request_id: int,
    data: ItvRequestValidation,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Admin: Approve or Reject an intervention request"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only Admins can validate requests")

    try:
        # Get request - check for PENDING_APPROVAL status
        request_result = await db.execute(
            select(OrdresIntervention).where(OrdresIntervention.id == request_id)
        )
        itv_request = request_result.scalar_one_or_none()
        if not itv_request:
            raise HTTPException(status_code=404, detail="Request not found")

        if itv_request.statut != "PENDING_APPROVAL":
            raise HTTPException(
                status_code=400,
                detail="Only pending approval requests can be validated",
            )

        itv_request.approved_by = current_user.id
        itv_request.approved_at = datetime.now(timezone.utc)

        if data.status == "REJECTED":
            await _handle_itv_rejected(db, itv_request, data.rejection_reason)
        elif data.status == "APPROVED":
            await _handle_itv_approved(db, itv_request, current_user)

        await db.commit()
        return {"message": f"Request {itv_request.statut}"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error validating request: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
