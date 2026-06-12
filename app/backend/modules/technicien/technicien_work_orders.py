from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from schemas.pagination import PaginatedResponse
from datetime import datetime
import logging
from pydantic import BaseModel

from core.database import get_db
from core.security import verify_technicien
from models.utilisateurs import Utilisateurs, UserRole
from models.machines import Machines
from models.ordres_travail import Ordres_travail, OrdreStatut
from models.ordres_intervention import Ordres_intervention
from models.planning_taches import Planning_taches
from models.machine_telemetry import MachineTelemetry
from services.audit import AuditService, AuditEntityType
from services.inventory import InventoryReservationService
from services.ml.recovery import PostMaintenanceRecoveryService
from schemas.stock import ConsumedPieceItem, ConsumedPieceDirect, PendingPieceDirect

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/technicien", tags=["technicien"])

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


@router.get("/work-orders", response_model=PaginatedResponse[WorkOrderResponse])
async def get_my_work_orders(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    current_user: Utilisateurs = Depends(verify_technicien),
    db: AsyncSession = Depends(get_db),
):
    """TECHNICIEN: List work orders assigned to this technician"""
    try:
        skip = (page - 1) * size

        # Count total - also check Ordres_travail.utilisateur_id directly
        count_query = select(func.count(Ordres_travail.id)).where(Ordres_travail.archived_at.is_(None))\
            .outerjoin(Ordres_intervention, Ordres_travail.id == Ordres_intervention.ordre_travail_id)\
            .where(
                (Ordres_intervention.technician_id == current_user.id) |
                (Ordres_travail.utilisateur_id == current_user.id)
            )
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = select(Ordres_travail, Machines.nom.label("machine_nom")).where(Ordres_travail.archived_at.is_(None))\
            .outerjoin(Ordres_intervention, Ordres_travail.id == Ordres_intervention.ordre_travail_id)\
            .outerjoin(Machines, Ordres_travail.machine_id == Machines.id)\
            .where(
                (Ordres_intervention.technician_id == current_user.id) |
                (Ordres_travail.utilisateur_id == current_user.id)
            )\
            .order_by(Ordres_travail.created_at.desc()).offset(skip).limit(size)
        
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
                source=getattr(wo, 'source', None),
                date_debut=wo.date_debut,
                date_fin=wo.date_fin,
            ) for wo, machine_nom in rows
        ]

        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            size=size
        )
    except Exception as e:
        logger.error(f"Error fetching work orders for technician: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.patch("/work-orders/{order_id}/start")
async def start_work_order(
    order_id: int,
    current_user: Utilisateurs = Depends(verify_technicien),
    db: AsyncSession = Depends(get_db),
):
    """TECHNICIEN: Start an assigned work order"""
    try:
        # Check if work order exists and belongs to this technician
        wo_result = await db.execute(
            select(Ordres_travail).where(Ordres_travail.id == order_id)
        )
        wo = wo_result.scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="Work order not found")
        
        # Allow if either utilisateur_id matches OR intervention link exists
        has_access = False
        if wo.utilisateur_id == current_user.id:
            has_access = True
        else:
            # Check via intervention link
            int_result = await db.execute(
                select(Ordres_intervention).where(
                    Ordres_intervention.ordre_travail_id == order_id,
                    Ordres_intervention.technician_id == current_user.id
                )
            )
            if int_result.scalar_one_or_none():
                has_access = True
        
        if not has_access:
            raise HTTPException(status_code=403, detail="You can only start work orders assigned to you")
        
        if wo.statut not in ["EN_ATTENTE", "ASSIGNÉ", "ASSIGNED"]:
            raise HTTPException(status_code=400, detail="Only pending/assigned orders can be started")

        previous_statut = wo.statut
        now = datetime.utcnow()
        wo.statut = OrdreStatut.IN_PROGRESS
        if not wo.date_debut:
            wo.date_debut = now
        
        # Update linked intervention if exists
        int_result = await db.execute(
            select(Ordres_intervention).where(
                Ordres_intervention.ordre_travail_id == order_id
            )
        )
        intervention = int_result.scalar_one_or_none()
        if intervention:
            intervention.statut = "EN_COURS"
            if not intervention.date_debut:
                intervention.date_debut = now
            
        await db.commit()

        try:
            await AuditService(db).log_update(
                entity_type=AuditEntityType.WORK_ORDER,
                entity_id=order_id,
                old_values={"statut": previous_statut},
                new_values={"statut": OrdreStatut.IN_PROGRESS},
                user_id=current_user.id,
                user_name=current_user.nom,
                entity_name=wo.titre,
            )
        except Exception:
            logger.warning("Audit log failed for technician start work order %s", order_id)

        return {"message": "Work order started", "statut": OrdreStatut.IN_PROGRESS}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error starting work order: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.patch("/work-orders/{order_id}/complete")
async def complete_work_order(
    order_id: int,
    payload: WorkOrderCompletePayload,
    current_user: Utilisateurs = Depends(verify_technicien),
    db: AsyncSession = Depends(get_db),
):
    """TECHNICIEN: Complete a work order with full PDCA data"""
    try:
        # Check if work order exists
        wo_result = await db.execute(select(Ordres_travail).where(Ordres_travail.id == order_id))
        wo = wo_result.scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="Work order not found")
        
        # Allow if either utilisateur_id matches OR intervention link exists
        has_access = False
        if wo.utilisateur_id == current_user.id:
            has_access = True
        else:
            int_result = await db.execute(
                select(Ordres_intervention).where(
                    Ordres_intervention.ordre_travail_id == order_id,
                    Ordres_intervention.technician_id == current_user.id
                )
            )
            if int_result.scalar_one_or_none():
                has_access = True
        
        if not has_access:
            raise HTTPException(status_code=403, detail="You can only complete work orders assigned to you")
        
        if wo.statut != OrdreStatut.IN_PROGRESS:
            raise HTTPException(status_code=400, detail="Only 'IN_PROGRESS' orders can be completed")

        now = datetime.utcnow()

        # Post-maintenance recovery: snapshot pre-fix health before completing.
        # Non-blocking — None silently if ML service is unavailable.
        try:
            _pre_fix_score = await PostMaintenanceRecoveryService(db).snapshot_health(
                wo.machine_id
            )
            if _pre_fix_score is not None:
                wo.health_score_at_completion = _pre_fix_score
        except Exception as _rec_exc:
            logger.warning(
                "Recovery completion snapshot failed for WO %s: %s",
                order_id, _rec_exc,
            )

        wo.statut = OrdreStatut.COMPLETED
        wo.date_fin = now
        wo.rapport = payload.rapport

        machine_obj = await db.scalar(select(Machines).where(Machines.id == wo.machine_id))
        if machine_obj:
            machine_obj.date_derniere_maintenance = now

        # Update linked intervention if exists
        int_result = await db.execute(
            select(Ordres_intervention).where(
                Ordres_intervention.ordre_travail_id == order_id
            )
        )
        intervention = int_result.scalar_one_or_none()
        if intervention:
            intervention.statut = "TERMINÉ"
            intervention.rapport = payload.rapport
            if not intervention.date_debut:
                intervention.date_debut = wo.date_debut or now
            intervention.date_fin = now
            
            intervention.intervention_type = payload.intervention_type
            intervention.root_cause_category = payload.root_cause_category
            intervention.root_cause_description = payload.root_cause_description
            intervention.actions_performed = payload.actions_performed
            intervention.legacy_parts_text = payload.parts_replaced  # legacy free-text fallback
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
                    select(Planning_taches).where(Planning_taches.id == intervention.planning_tache_id)
                )
                if tache:
                    tache.statut = "COMPLETED"

        # Save telemetry if any telemetry field is provided
        if any([
            payload.air_temperature,
            payload.process_temperature,
            payload.rotational_speed,
            payload.torque,
            payload.tool_wear,
        ]):
            telemetry = MachineTelemetry(
                machine_id=wo.machine_id,
                work_order_id=wo.id,
                technician_id=current_user.id,
                air_temperature=payload.air_temperature or 0,
                process_temperature=payload.process_temperature or 0,
                rotational_speed=payload.rotational_speed or 0,
                torque=payload.torque or 0,
                tool_wear=payload.tool_wear or 0,
                recorded_at=now,
                notes=payload.telemetry_notes,
            )
            db.add(telemetry)

        # ── Ad-hoc consumption (no prior reservation) ─────────────────────
        if intervention and payload.parts_consumed_direct:
            try:
                from models.required_pieces import RequiredPiece
                from models.consumed_pieces import ConsumedPiece
                from services.inventory import InventoryReservationService as _IRS
                from services.inventory.stock import StockService as _Stock
                from sqlalchemy import select as _select
                from models.pieces import Piece as _Piece
                from decimal import Decimal as _D
                stock_svc = _Stock(db)
                for di in payload.parts_consumed_direct:
                    piece = await db.scalar(_select(_Piece).where(_Piece.id == di.piece_id))
                    if piece is None:
                        raise ValueError(f"Pièce {di.piece_id} introuvable")
                    unit = di.unit or piece.default_unit or "pcs"
                    qty = _D(str(di.quantity)).quantize(_D("0.01"))
                    rp = RequiredPiece(
                        intervention_id=intervention.id,
                        piece_id=di.piece_id,
                        quantity_planned=qty,
                        unit=unit,
                        quantity_reserved=_D("0"),
                        approved=True,
                    )
                    db.add(rp)
                    await db.flush()
                    await stock_svc.consume_stock(
                        piece_id=di.piece_id,
                        quantity=qty,
                        intervention_id=intervention.id,
                        reference=f"OT-itv-{intervention.id}-direct",
                        unit=unit,
                        auto_commit=False,
                    )
                    cp = ConsumedPiece(
                        intervention_id=intervention.id,
                        required_piece_id=rp.id,
                        piece_id=di.piece_id,
                        quantity_used=qty,
                        quantity_returned=_D("0"),
                        quantity_wasted=_D("0"),
                        unit=unit,
                        disposition="used",
                        notes=di.notes,
                    )
                    db.add(cp)
                    await _IRS(db)._auto_link_piece_to_machine(
                        piece_id=di.piece_id, intervention_id=intervention.id
                    )
                await db.flush()
            except ValueError as ve:
                await db.rollback()
                logger.warning("Direct parts consumption failed for OT %s: %s", order_id, ve)
                raise HTTPException(status_code=400, detail=f"Stock insuffisant: {ve}")
            except Exception as exc:
                await db.rollback()
                logger.error("Direct parts consumption error for OT %s: %s", order_id, exc, exc_info=True)
                raise HTTPException(status_code=500, detail="Échec consommation directe")

        # ── Pending pieces submitted at completion (uncatalogued) ─────────
        if intervention and payload.pending_pieces_direct:
            try:
                from services.inventory import PendingPieceService as _PPS
                pending_svc = _PPS(db)
                for pp_item in payload.pending_pieces_direct:
                    if not pp_item.name or not pp_item.name.strip():
                        continue
                    await pending_svc.create_with_placeholder(
                        name=pp_item.name,
                        quantity=pp_item.quantity,
                        unit=pp_item.unit,
                        category=pp_item.category,
                        notes=pp_item.notes,
                        intervention_id=intervention.id,
                        submitted_by=current_user.id,
                        auto_commit=False,
                    )
            except Exception as exc:
                logger.warning(f"Pending direct submit failed for OT {order_id}: {exc}", exc_info=True)

        # ── Atomic parts consumption (pre-reserved) ───────────────────────
        # If the technician submitted parts_consumed, fulfill each reservation
        # within the same transaction. Any insufficiency rolls back the entire
        # work-order completion (no half-state).
        if intervention and payload.parts_consumed:
            try:
                reservation_svc = InventoryReservationService(db)
                for item in payload.parts_consumed:
                    await reservation_svc.fulfill_reservation(
                        required_piece_id=item.required_piece_id,
                        quantity_used=item.quantity_used,
                        quantity_returned=item.quantity_returned,
                        quantity_wasted=item.quantity_wasted,
                        disposition=item.disposition,
                        notes=item.notes,
                        auto_commit=False,
                    )
                # invalidate forecast cache after real consumption recorded
                try:
                    from modules.ml.services.demand_forecast import invalidate_forecast_cache
                    invalidate_forecast_cache()
                except Exception:
                    pass
            except ValueError as ve:
                await db.rollback()
                logger.warning("Parts consumption failed for OT %s: %s", order_id, ve)
                raise HTTPException(status_code=400, detail=f"Stock insuffisant: {ve}")

        await db.commit()

        try:
            await AuditService(db).log_update(
                entity_type=AuditEntityType.WORK_ORDER,
                entity_id=order_id,
                old_values={"statut": "EN_COURS"},
                new_values={"statut": "TERMINÉ", "rapport": payload.rapport},
                user_id=current_user.id,
                user_name=current_user.nom,
                entity_name=wo.titre,
            )
        except Exception:
            logger.warning("Audit log failed for technician complete work order %s", order_id)

        return {"message": "Work order completed via PDCA form", "statut": "TERMINÉ"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error completing work order: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
