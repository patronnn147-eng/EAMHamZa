from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List, Optional, Annotated
from schemas.pagination import PaginatedResponse
from datetime import datetime, timezone
import logging
from pydantic import BaseModel, field_validator

from core.database import get_db
from core.security import verify_technicien
from models.utilisateurs import Utilisateurs
from models.machines import Machines
from models.ordres_travail import OrdresTravail, OrdreStatut
from models.ordres_intervention import OrdresIntervention
from models.planning_taches import PlanningTaches
from models.machine_telemetry import MachineTelemetry
from models.machine_status import MACHINE_STATUSES
from services.audit import AuditService, AuditEntityType
from services.inventory import InventoryReservationService
from services.ml.recovery import PostMaintenanceRecoveryService
from modules.shared.services.machine_status_requests import create_status_change_request
from schemas.stock import ConsumedPieceItem, ConsumedPieceDirect, PendingPieceDirect

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/technicien", tags=["technicien"])

_INTERNAL_SERVER_ERROR_MSG = "Internal server error"
_STATUT_TERMINE = "TERMINÉ"


class WorkOrderResponse(BaseModel):
    id: int
    titre: str
    description: Optional[str] = None
    priorite: str
    statut: str
    machine_id: int
    machine_nom: Optional[str] = None
    created_at: datetime
    date_echeance: Optional[datetime] = None
    source: Optional[str] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None


class WorkOrderCompletePayload(BaseModel):
    rapport: str

    # Enhanced Report fields
    intervention_type: Optional[str] = None
    root_cause_category: Optional[str] = None
    root_cause_description: Optional[str] = None
    actions_performed: Optional[str] = None
    parts_replaced: Optional[str] = None
    tools_used: Optional[str] = None
    machine_status_after: Optional[str] = None

    @field_validator("machine_status_after")
    @classmethod
    def _validate_machine_status_after(cls, v):
        if v is not None and v not in MACHINE_STATUSES:
            raise ValueError(f"machine_status_after must be one of {MACHINE_STATUSES}")
        return v

    # PDCA Specific
    plan_hypothesis: Optional[str] = None
    check_resolved: Optional[bool] = None
    check_verification_method: Optional[str] = None
    act_preventive_actions: Optional[str] = None
    act_recommendations: Optional[str] = None

    # Machine Telemetry fields (all optional)
    air_temperature: Optional[float] = None
    process_temperature: Optional[float] = None
    rotational_speed: Optional[int] = None
    torque: Optional[float] = None
    tool_wear: Optional[int] = None
    telemetry_notes: Optional[str] = None
    ml_prediction_matched: Optional[bool] = None

    # ── NEW: structured parts consumption (replaces free-text parts_replaced) ──
    # Each item links to a required_piece (reservation) and carries the split
    # used/returned/wasted quantities. When present, the completion handler
    # delegates to InventoryReservationService.fulfill_reservation to apply
    # the stock movements atomically.
    parts_consumed: Optional[List[ConsumedPieceItem]] = None
    # NEW: ad-hoc consumption from catalog (not pre-reserved) — see ConsumedPieceDirect docstring
    parts_consumed_direct: Optional[List[ConsumedPieceDirect]] = None
    # NEW: uncatalogued pieces submitted at completion time
    pending_pieces_direct: Optional[List[PendingPieceDirect]] = None


@router.get("/work-orders", response_model=PaginatedResponse[WorkOrderResponse], responses={500: {"description": "Internal server error"}})
async def get_my_work_orders(
    *, page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 10,
    current_user: Annotated[Utilisateurs, Depends(verify_technicien)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """TECHNICIEN: List work orders assigned to this technician"""
    try:
        skip = (page - 1) * size

        # Count total - also check OrdresTravail.utilisateur_id directly
        count_query = (
            select(func.count(OrdresTravail.id))
            .where(OrdresTravail.archived_at.is_(None))
            .outerjoin(
                OrdresIntervention,
                OrdresTravail.id == OrdresIntervention.ordre_travail_id,
            )
            .where(
                (OrdresIntervention.technician_id == current_user.id)
                | (OrdresTravail.utilisateur_id == current_user.id)
            )
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = (
            select(OrdresTravail, Machines.nom.label("machine_nom"))
            .where(OrdresTravail.archived_at.is_(None))
            .outerjoin(
                OrdresIntervention,
                OrdresTravail.id == OrdresIntervention.ordre_travail_id,
            )
            .outerjoin(Machines, OrdresTravail.machine_id == Machines.id)
            .where(
                (OrdresIntervention.technician_id == current_user.id)
                | (OrdresTravail.utilisateur_id == current_user.id)
            )
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
                created_at=wo.created_at,
                date_echeance=wo.date_echeance,
                source=getattr(wo, "source", None),
                date_debut=wo.date_debut,
                date_fin=wo.date_fin,
            )
            for wo, machine_nom in rows
        ]

        return PaginatedResponse.create(items=items, total=total, page=page, size=size)
    except Exception as e:
        logger.exception(f"Error fetching work orders for technician: {str(e)}")
        raise HTTPException(status_code=500, detail=_INTERNAL_SERVER_ERROR_MSG)


@router.patch("/work-orders/{order_id}/start", responses={400: {"description": "Only pending/assigned orders can be started"}, 403: {"description": "You can only start work orders assigned to you"}, 404: {"description": "Work order not found"}, 500: {"description": "Internal server error"}})
async def start_work_order(
    order_id: int,
    current_user: Annotated[Utilisateurs, Depends(verify_technicien)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """TECHNICIEN: Start an assigned work order"""
    try:
        wo = (await db.execute(
            select(OrdresTravail).where(OrdresTravail.id == order_id)
        )).scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="Work order not found")
        if not await _check_wo_access(db, wo, current_user.id, order_id):
            raise HTTPException(status_code=403, detail="You can only start work orders assigned to you")
        if wo.statut not in ["EN_ATTENTE", "ASSIGNÉ", "ASSIGNED"]:
            raise HTTPException(status_code=400, detail="Only pending/assigned orders can be started")

        previous_statut = wo.statut
        now = datetime.now(timezone.utc)
        wo.statut = OrdreStatut.IN_PROGRESS
        if not wo.date_debut:
            wo.date_debut = now

        intervention = (await db.execute(
            select(OrdresIntervention).where(OrdresIntervention.ordre_travail_id == order_id)
        )).scalar_one_or_none()
        if intervention:
            _update_intervention_on_start(intervention, now)

        await db.commit()
        await _try_audit_start(db, order_id, previous_statut, wo, current_user.id, current_user.nom)
        return {"message": "Work order started", "statut": OrdreStatut.IN_PROGRESS}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error starting work order: {str(e)}")
        raise HTTPException(status_code=500, detail=_INTERNAL_SERVER_ERROR_MSG)


def _update_intervention_on_start(intervention: OrdresIntervention, now) -> None:
    """Set intervention status and start date when a WO is started."""
    intervention.statut = "EN_COURS"
    if not intervention.date_debut:
        intervention.date_debut = now


async def _try_audit_start(
    db: AsyncSession, order_id: int, previous_statut: str, wo, user_id: int, nom: str
) -> None:
    """Fire-and-forget audit log for WO start."""
    try:
        await AuditService(db).log_update(
            entity_type=AuditEntityType.WORK_ORDER,
            entity_id=order_id,
            old_values={"statut": previous_statut},
            new_values={"statut": OrdreStatut.IN_PROGRESS},
            user_id=user_id,
            user_name=nom,
            entity_name=wo.titre,
        )
    except Exception:
        logger.warning("Audit log failed for technician start work order %s", order_id)


async def _snapshot_pre_completion(db: AsyncSession, wo, order_id: int) -> None:
    """Non-blocking health snapshot before marking WO complete."""
    try:
        score = await PostMaintenanceRecoveryService(db).snapshot_health(wo.machine_id)
        if score is not None:
            wo.health_score_at_completion = score
    except Exception as exc:
        logger.warning("Recovery completion snapshot failed for WO %s: %s", order_id, exc)


async def _try_audit_complete(
    db: AsyncSession, order_id: int, payload, wo, user_id: int, nom: str
) -> None:
    """Fire-and-forget audit log for WO completion."""
    try:
        await AuditService(db).log_update(
            entity_type=AuditEntityType.WORK_ORDER,
            entity_id=order_id,
            old_values={"statut": "EN_COURS"},
            new_values={"statut": _STATUT_TERMINE, "rapport": payload.rapport},
            user_id=user_id,
            user_name=nom,
            entity_name=wo.titre,
        )
    except Exception:
        logger.warning("Audit log failed for technician complete work order %s", order_id)


async def _check_wo_access(db: AsyncSession, wo: OrdresTravail, user_id: int, order_id: int) -> bool:
    """Return True if user owns WO or is linked via intervention."""
    if wo.utilisateur_id == user_id:
        return True
    result = await db.execute(
        select(OrdresIntervention).where(
            OrdresIntervention.ordre_travail_id == order_id,
            OrdresIntervention.technician_id == user_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def _update_intervention_fields(db: AsyncSession, intervention: OrdresIntervention,
                                      payload: "WorkOrderCompletePayload", wo_date_debut, now) -> None:
    """Apply PDCA + extended fields to linked intervention."""
    intervention.statut = _STATUT_TERMINE
    intervention.rapport = payload.rapport
    if not intervention.date_debut:
        intervention.date_debut = wo_date_debut or now
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
    if payload.ml_prediction_matched is not None:
        intervention.ml_prediction_matched = payload.ml_prediction_matched
    if intervention.planning_tache_id:
        tache = await db.scalar(
            select(PlanningTaches).where(PlanningTaches.id == intervention.planning_tache_id)
        )
        if tache:
            tache.statut = "COMPLETED"


def _add_telemetry_if_present(db: AsyncSession, wo: OrdresTravail,
                               technician_id: int, payload: "WorkOrderCompletePayload", now) -> None:
    """Add MachineTelemetry row if any sensor field is provided."""
    if not any([payload.air_temperature, payload.process_temperature,
                payload.rotational_speed, payload.torque, payload.tool_wear]):
        return
    db.add(MachineTelemetry(
        machine_id=wo.machine_id,
        work_order_id=wo.id,
        technician_id=technician_id,
        air_temperature=payload.air_temperature or 0,
        process_temperature=payload.process_temperature or 0,
        rotational_speed=payload.rotational_speed or 0,
        torque=payload.torque or 0,
        tool_wear=payload.tool_wear or 0,
        recorded_at=now,
        notes=payload.telemetry_notes,
    ))


async def _consume_direct_parts(db: AsyncSession, intervention: OrdresIntervention,
                                payload: "WorkOrderCompletePayload", order_id: int) -> None:
    """Ad-hoc parts consumption (no prior reservation). Raises HTTPException on failure."""
    if not (intervention and payload.parts_consumed_direct):
        return
    try:
        from models.required_pieces import RequiredPiece
        from models.consumed_pieces import ConsumedPiece
        from services.inventory import InventoryReservationService as _IRS
        from services.inventory.stock import StockService as _Stock
        from models.pieces import Piece as _Piece
        from decimal import Decimal as _D

        stock_svc = _Stock(db)
        for di in payload.parts_consumed_direct:
            piece = await db.scalar(select(_Piece).where(_Piece.id == di.piece_id))
            if piece is None:
                raise ValueError(f"Pièce {di.piece_id} introuvable")
            unit = di.unit or piece.default_unit or "pcs"
            qty = _D(str(di.quantity)).quantize(_D("0.01"))
            rp = RequiredPiece(
                intervention_id=intervention.id, piece_id=di.piece_id,
                quantity_planned=qty, unit=unit, quantity_reserved=_D("0"), approved=True,
            )
            db.add(rp)
            await db.flush()
            await stock_svc.consume_stock(
                piece_id=di.piece_id, quantity=qty, intervention_id=intervention.id,
                reference=f"OT-itv-{intervention.id}-direct", unit=unit, auto_commit=False,
            )
            db.add(ConsumedPiece(
                intervention_id=intervention.id, required_piece_id=rp.id,
                piece_id=di.piece_id, quantity_used=qty, quantity_returned=_D("0"),
                quantity_wasted=_D("0"), unit=unit, disposition="used", notes=di.notes,
            ))
            await _IRS(db)._auto_link_piece_to_machine(piece_id=di.piece_id, intervention_id=intervention.id)
        await db.flush()
    except ValueError as ve:
        await db.rollback()
        logger.warning("Direct parts consumption failed for OT %s: %s", order_id, ve)
        raise HTTPException(status_code=400, detail=f"Stock insuffisant: {ve}")
    except Exception as exc:
        await db.rollback()
        logger.exception("Direct parts consumption error for OT %s: %s", order_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Échec consommation directe")


async def _submit_pending_pieces(db: AsyncSession, intervention: OrdresIntervention,
                                  payload: "WorkOrderCompletePayload", user_id: int, order_id: int) -> None:
    """Submit uncatalogued pieces. Non-fatal on failure."""
    if not (intervention and payload.pending_pieces_direct):
        return
    try:
        from services.inventory import PendingPieceService as _PPS
        pending_svc = _PPS(db)
        for pp_item in payload.pending_pieces_direct:
            if not pp_item.name or not pp_item.name.strip():
                continue
            await pending_svc.create_with_placeholder(
                name=pp_item.name, quantity=pp_item.quantity, unit=pp_item.unit,
                category=pp_item.category, notes=pp_item.notes,
                intervention_id=intervention.id, submitted_by=user_id, auto_commit=False,
            )
    except Exception as exc:
        logger.warning(f"Pending direct submit failed for OT {order_id}: {exc}", exc_info=True)


async def _fulfill_reserved_parts(db: AsyncSession, intervention: OrdresIntervention,
                                   payload: "WorkOrderCompletePayload", order_id: int) -> None:
    """Fulfill pre-reserved parts. Raises HTTPException on stock insufficiency."""
    if not (intervention and payload.parts_consumed):
        return
    try:
        reservation_svc = InventoryReservationService(db)
        for item in payload.parts_consumed:
            await reservation_svc.fulfill_reservation(
                required_piece_id=item.required_piece_id, quantity_used=item.quantity_used,
                quantity_returned=item.quantity_returned, quantity_wasted=item.quantity_wasted,
                disposition=item.disposition, notes=item.notes, auto_commit=False,
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


@router.patch("/work-orders/{order_id}/complete", responses={400: {"description": "Only 'IN_PROGRESS' orders can be completed"}, 403: {"description": "You can only complete work orders assigned to you"}, 404: {"description": "Work order not found"}, 500: {"description": "Échec consommation directe; Internal server error"}})
async def complete_work_order(
    order_id: int,
    payload: WorkOrderCompletePayload,
    current_user: Annotated[Utilisateurs, Depends(verify_technicien)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """TECHNICIEN: Complete a work order with full PDCA data"""
    try:
        wo = (await db.execute(select(OrdresTravail).where(OrdresTravail.id == order_id))).scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="Work order not found")
        if not await _check_wo_access(db, wo, current_user.id, order_id):
            raise HTTPException(status_code=403, detail="You can only complete work orders assigned to you")
        if wo.statut != OrdreStatut.IN_PROGRESS:
            raise HTTPException(status_code=400, detail="Only 'IN_PROGRESS' orders can be completed")

        now = datetime.now(timezone.utc)

        await _snapshot_pre_completion(db, wo, order_id)
        wo.statut = OrdreStatut.COMPLETED
        wo.date_fin = now
        wo.rapport = payload.rapport

        machine_obj = await db.scalar(select(Machines).where(Machines.id == wo.machine_id))
        if machine_obj:
            machine_obj.date_derniere_maintenance = now

        intervention = (await db.execute(
            select(OrdresIntervention).where(OrdresIntervention.ordre_travail_id == order_id)
        )).scalar_one_or_none()
        if intervention:
            await _update_intervention_fields(db, intervention, payload, wo.date_debut, now)
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

        _add_telemetry_if_present(db, wo, current_user.id, payload, now)
        await _consume_direct_parts(db, intervention, payload, order_id)
        await _submit_pending_pieces(db, intervention, payload, current_user.id, order_id)
        await _fulfill_reserved_parts(db, intervention, payload, order_id)

        await db.commit()
        await _try_audit_complete(db, order_id, payload, wo, current_user.id, current_user.nom)
        return {"message": "Work order completed via PDCA form", "statut": _STATUT_TERMINE}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error completing work order: {str(e)}")
        raise HTTPException(status_code=500, detail=_INTERNAL_SERVER_ERROR_MSG)
