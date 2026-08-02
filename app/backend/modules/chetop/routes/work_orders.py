import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.pagination import PaginatedResponse
from sqlalchemy import func as sa_func

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs, UserRole
from models.ordres_travail import OrdresTravail
from models.ordres_intervention import OrdresIntervention
from models.machines import Machines
from models.machine_telemetry import MachineTelemetry
from services.audit import AuditService, AuditEntityType
from services.inventory import InventoryReservationService
from services.ml.recovery import PostMaintenanceRecoveryService
from modules.shared.services.machine_status_requests import create_status_change_request
from schemas.stock import ConsumedPieceItem
from ..schemas import WorkOrderResponse, WorkOrderCompletePayload
from typing import Annotated

router = APIRouter(prefix="/api/v1/chetop", tags=["chetop"])
logger = logging.getLogger(__name__)

_INTERNAL_SERVER_ERROR_MSG = "Internal server error"
_STATUT_TERMINE = "TERMINÉ"


@router.get("/work-orders", response_model=PaginatedResponse[WorkOrderResponse], responses={403: {"description": "Forbidden"}, 500: {"description": "Internal server error"}})
async def get_my_work_orders(
    *, page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 10,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """CHETOP: List work orders generated from my intervention requests"""
    if current_user.role != UserRole.CHETOP:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        skip = (page - 1) * size

        count_query = (
            select(sa_func.count(OrdresTravail.id))
            .where(OrdresTravail.archived_at.is_(None))
            .join(
                OrdresIntervention,
                OrdresTravail.id == OrdresIntervention.ordre_travail_id,
            )
            .where(OrdresIntervention.requested_by == current_user.id)
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = (
            select(
                OrdresTravail,
                Machines.nom.label("machine_nom"),
                Utilisateurs.nom.label("utilisateur_nom"),
            )
            .join(
                OrdresIntervention,
                OrdresTravail.id == OrdresIntervention.ordre_travail_id,
            )
            .outerjoin(Machines, OrdresTravail.machine_id == Machines.id)
            .outerjoin(Utilisateurs, OrdresTravail.utilisateur_id == Utilisateurs.id)
            .where(OrdresIntervention.requested_by == current_user.id)
            .where(OrdresTravail.archived_at.is_(None))
            .order_by(OrdresTravail.created_at.desc())
            .offset(skip)
            .limit(size)
        )

        # nosemgrep: python.fastapi.db.generic-sql-fastapi -- `query` is a SQLAlchemy
        # Core select() built from ORM joins/column comparisons above; no raw SQL or
        # string interpolation is involved.
        result = await db.execute(query)
        rows = result.all()

        items = [
            WorkOrderResponse(
                id=wo.id,
                titre=wo.titre,
                description=wo.description,
                priorite=wo.priorite,
                statut=wo.statut,
                machine_id=wo.machine_id,
                machine_nom=machine_nom,
                utilisateur_nom=utilisateur_nom,
                created_at=wo.created_at,
                date_debut=wo.date_debut,
                date_fin=wo.date_fin,
            )
            for wo, machine_nom, utilisateur_nom in rows
        ]

        return PaginatedResponse.create(items=items, total=total, page=page, size=size)
    except Exception as e:
        logger.exception(f"Error fetching work orders: {str(e)}")
        raise HTTPException(status_code=500, detail=_INTERNAL_SERVER_ERROR_MSG)


@router.patch("/work-orders/{order_id}/start", responses={400: {"description": "Only 'ASSIGNÉ' orders can be started"}, 403: {"description": "Forbidden; You can only start work orders you requested"}, 404: {"description": "Work order not found"}, 500: {"description": "Internal server error"}})
async def start_work_order(
    order_id: int,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """CHETOP: Start a work order"""
    if current_user.role != UserRole.CHETOP:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        # Verify ownership via intervention request - check requested_by not technician_id
        check_query = (
            select(OrdresIntervention)
            .where(OrdresIntervention.ordre_travail_id == order_id)
            .where(OrdresIntervention.requested_by == current_user.id)
        )

        check_result = await db.execute(check_query)
        if not check_result.scalar_one_or_none():
            raise HTTPException(
                status_code=403, detail="You can only start work orders you requested"
            )

        wo_result = await db.execute(
            select(OrdresTravail).where(OrdresTravail.id == order_id)
        )
        wo = wo_result.scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="Work order not found")

        if wo.statut != "ASSIGNÉ":
            raise HTTPException(
                status_code=400, detail="Only 'ASSIGNÉ' orders can be started"
            )

        wo.statut = "EN_COURS"
        wo.date_debut = datetime.now(timezone.utc)
        await db.commit()

        try:
            await AuditService(db).log_update(
                entity_type=AuditEntityType.WORK_ORDER,
                entity_id=order_id,
                old_values={"statut": "ASSIGNÉ"},
                new_values={"statut": "EN_COURS"},
                user_id=current_user.id,
                user_name=current_user.nom,
            )
        except Exception:
            logger.warning("Audit log failed for start work order %s", order_id)

        return {"message": "Work order started", "statut": "EN_COURS"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error starting work order: {str(e)}")
        raise HTTPException(status_code=500, detail=_INTERNAL_SERVER_ERROR_MSG)


async def _try_snapshot_health_before_complete(db: AsyncSession, wo, order_id: int) -> None:
    """Capture pre-fix health score on the WO. Non-blocking — failures logged only."""
    try:
        score = await PostMaintenanceRecoveryService(db).snapshot_health(wo.machine_id)
        if score is not None:
            wo.health_score_at_completion = score
    except Exception as exc:
        logger.warning("Recovery completion snapshot failed for WO %s: %s", order_id, exc)


def _apply_intervention_completion_fields(intervention, payload, wo, now) -> None:
    """Write all PDCA completion fields to the intervention ORM object."""
    intervention.statut = _STATUT_TERMINE
    intervention.rapport = payload.rapport
    if not intervention.date_debut:
        intervention.date_debut = wo.date_debut or now
    intervention.date_fin = now
    intervention.intervention_type = payload.intervention_type
    intervention.root_cause_category = payload.root_cause_category
    intervention.root_cause_description = payload.root_cause_description
    intervention.actions_performed = payload.actions_performed
    intervention.legacy_parts_text = payload.parts_replaced
    intervention.tools_used = payload.tools_used
    intervention.machine_status_after = payload.machine_status_after
    intervention.plan_hypothesis = payload.plan_hypothesis
    intervention.check_resolved = payload.check_resolved
    intervention.check_verification_method = payload.check_verification_method
    intervention.act_preventive_actions = payload.act_preventive_actions
    intervention.act_recommendations = payload.act_recommendations


def _add_telemetry_if_present(db, payload, wo, order_id: int, now, technician_id: int) -> None:
    """Insert a MachineTelemetry row if any sensor value was submitted."""
    has_telemetry = any(
        v is not None
        for v in (
            payload.air_temperature, payload.process_temperature,
            payload.rotational_speed, payload.torque, payload.tool_wear,
        )
    )
    if has_telemetry:
        db.add(MachineTelemetry(
            machine_id=wo.machine_id,
            work_order_id=order_id,
            technician_id=technician_id,
            air_temperature=payload.air_temperature or 0,
            process_temperature=payload.process_temperature or 0,
            rotational_speed=payload.rotational_speed or 0,
            torque=payload.torque or 0,
            tool_wear=payload.tool_wear or 0,
            recorded_at=now,
            notes=f"Work order #{order_id} completion",
        ))


async def _apply_parts_consumption(db: AsyncSession, intervention, payload, order_id: int) -> None:
    """Fulfill parts consumption reservations for the WO completion (atomic)."""
    if not (intervention and getattr(payload, "parts_consumed", None)):
        return
    try:
        reservation_svc = InventoryReservationService(db)
        for raw_item in payload.parts_consumed:
            item = ConsumedPieceItem(**raw_item) if isinstance(raw_item, dict) else raw_item
            await reservation_svc.fulfill_reservation(
                required_piece_id=item.required_piece_id,
                quantity_used=item.quantity_used,
                quantity_returned=item.quantity_returned,
                quantity_wasted=item.quantity_wasted,
                disposition=item.disposition,
                notes=item.notes,
                auto_commit=False,
            )
        try:
            from modules.ml.services.demand_forecast import invalidate_forecast_cache
            invalidate_forecast_cache()
        except Exception:
            pass
    except ValueError as ve:
        await db.rollback()
        logger.warning("Parts consumption failed for OT %s: %s", order_id, ve)
        raise HTTPException(status_code=400, detail=f"Stock insuffisant: {ve}")


async def _try_audit_chetop_complete(
    db: AsyncSession, order_id: int, payload, user_id: int, user_name
) -> None:
    """Fire-and-forget audit log for CHETOP WO completion."""
    try:
        await AuditService(db).log_update(
            entity_type=AuditEntityType.WORK_ORDER,
            entity_id=order_id,
            old_values={"statut": "EN_COURS"},
            new_values={"statut": _STATUT_TERMINE, "rapport": payload.rapport},
            user_id=user_id,
            user_name=user_name,
        )
    except Exception:
        logger.warning("Audit log failed for complete work order %s", order_id)


@router.patch("/work-orders/{order_id}/complete", responses={400: {"description": "Only 'EN_COURS' orders can be completed"}, 403: {"description": "Forbidden; You can only complete work orders you requested"}, 404: {"description": "Work order not found"}, 500: {"description": "Internal server error"}})
async def complete_work_order(
    order_id: int,
    payload: WorkOrderCompletePayload,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """CHETOP: Complete a work order"""
    if current_user.role != UserRole.CHETOP:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        check_result = await db.execute(
            select(OrdresIntervention)
            .where(OrdresIntervention.ordre_travail_id == order_id)
            .where(OrdresIntervention.requested_by == current_user.id)
        )
        intervention = check_result.scalar_one_or_none()
        if not intervention:
            raise HTTPException(
                status_code=403,
                detail="You can only complete work orders you requested",
            )

        wo = (await db.execute(select(OrdresTravail).where(OrdresTravail.id == order_id))).scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="Work order not found")

        if wo.statut != "EN_COURS":
            raise HTTPException(
                status_code=400, detail="Only 'EN_COURS' orders can be completed"
            )

        now = datetime.now(timezone.utc)
        await _try_snapshot_health_before_complete(db, wo, order_id)

        wo.statut = _STATUT_TERMINE
        wo.date_fin = now
        wo.rapport = payload.rapport

        machine_obj = await db.scalar(select(Machines).where(Machines.id == wo.machine_id))
        if machine_obj:
            machine_obj.date_derniere_maintenance = now

        _apply_intervention_completion_fields(intervention, payload, wo, now)
        if payload.machine_status_after:
            try:
                await create_status_change_request(
                    machine_id=wo.machine_id,
                    to_status=payload.machine_status_after,
                    requested_by=current_user.id,
                    source_intervention_id=intervention.id,
                    db=db,
                )
            except Exception:
                logger.warning(
                    f"Machine status change request failed for WO {order_id}"
                )
        _add_telemetry_if_present(db, payload, wo, order_id, now, current_user.id)
        await _apply_parts_consumption(db, intervention, payload, order_id)

        await db.commit()
        await _try_audit_chetop_complete(db, order_id, payload, current_user.id, current_user.nom)

        return {"message": "Work order completed", "statut": _STATUT_TERMINE}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error completing work order: {str(e)}")
        raise HTTPException(status_code=500, detail=_INTERNAL_SERVER_ERROR_MSG)
