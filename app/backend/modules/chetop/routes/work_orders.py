import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.pagination import PaginatedResponse
from sqlalchemy import func as sa_func

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs, UserRole
from models.ordres_travail import Ordres_travail
from models.ordres_intervention import Ordres_intervention
from models.machines import Machines
from models.machine_telemetry import MachineTelemetry
from services.audit import AuditService, AuditEntityType
from services.inventory import InventoryReservationService
from services.ml.recovery import PostMaintenanceRecoveryService
from schemas.stock import ConsumedPieceItem
from ..schemas import WorkOrderResponse, WorkOrderCompletePayload

router = APIRouter(prefix="/api/v1/chetop", tags=["chetop"])
logger = logging.getLogger(__name__)


@router.get("/work-orders", response_model=PaginatedResponse[WorkOrderResponse])
async def get_my_work_orders(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """CHETOP: List work orders generated from my intervention requests"""
    if current_user.role != UserRole.CHETOP:
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        skip = (page - 1) * size

        count_query = select(sa_func.count(Ordres_travail.id)).where(Ordres_travail.archived_at.is_(None))\
            .join(Ordres_intervention, Ordres_travail.id == Ordres_intervention.ordre_travail_id)\
            .where(Ordres_intervention.requested_by == current_user.id)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        query = select(Ordres_travail, Machines.nom.label("machine_nom"))\
            .join(Ordres_intervention, Ordres_travail.id == Ordres_intervention.ordre_travail_id)\
            .outerjoin(Machines, Ordres_travail.machine_id == Machines.id)\
            .where(Ordres_intervention.requested_by == current_user.id)\
            .where(Ordres_travail.archived_at.is_(None))\
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
                date_debut=wo.date_debut,
                date_fin=wo.date_fin,
            ) for wo, machine_nom in rows
        ]

        return PaginatedResponse.create(items=items, total=total, page=page, size=size)
    except Exception as e:
        logger.error(f"Error fetching work orders: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/work-orders/{order_id}/start")
async def start_work_order(
    order_id: int,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """CHETOP: Start a work order"""
    if current_user.role != UserRole.CHETOP:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        # Verify ownership via intervention request - check requested_by not technician_id
        check_query = select(Ordres_intervention)\
            .where(Ordres_intervention.ordre_travail_id == order_id)\
            .where(Ordres_intervention.requested_by == current_user.id)
        
        check_result = await db.execute(check_query)
        if not check_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="You can only start work orders you requested")
            
        wo_result = await db.execute(select(Ordres_travail).where(Ordres_travail.id == order_id))
        wo = wo_result.scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="Work order not found")
        
        if wo.statut != "ASSIGNÉ":
            raise HTTPException(status_code=400, detail="Only 'ASSIGNÉ' orders can be started")
            
        wo.statut = "EN_COURS"
        wo.date_debut = datetime.utcnow()
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
        logger.error(f"Error starting work order: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/work-orders/{order_id}/complete")
async def complete_work_order(
    order_id: int,
    payload: WorkOrderCompletePayload,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """CHETOP: Complete a work order"""
    if current_user.role != UserRole.CHETOP:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        # Verify ownership via intervention request - check requested_by not technician_id
        check_query = select(Ordres_intervention)\
            .where(Ordres_intervention.ordre_travail_id == order_id)\
            .where(Ordres_intervention.requested_by == current_user.id)
        
        check_result = await db.execute(check_query)
        intervention = check_result.scalar_one_or_none()
        if not intervention:
            raise HTTPException(status_code=403, detail="You can only complete work orders you requested")
            
        wo_result = await db.execute(select(Ordres_travail).where(Ordres_travail.id == order_id))
        wo = wo_result.scalar_one_or_none()
        if not wo:
            raise HTTPException(status_code=404, detail="Work order not found")
        
        if wo.statut != "EN_COURS":
            raise HTTPException(status_code=400, detail="Only 'EN_COURS' orders can be completed")
            
        now = datetime.utcnow()

        # Post-maintenance recovery: capture pre-fix health state right before
        # the WO is marked complete. Non-blocking — None if ML service is down.
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

        wo.statut = "TERMINÉ"
        wo.date_fin = now
        wo.rapport = payload.rapport

        machine_obj = await db.scalar(select(Machines).where(Machines.id == wo.machine_id))
        if machine_obj:
            machine_obj.date_derniere_maintenance = now

        # Also update the associated intervention with enhanced fields
        intervention.statut = "TERMINÉ"
        intervention.rapport = payload.rapport
        if not intervention.date_debut:
            intervention.date_debut = wo.date_debut or now
        intervention.date_fin = now
        
        # New Report and PDCA fields
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
        
        # =============================================
        # Task 4+5: Save telemetry to logs AND update machine current state
        # =============================================
        has_telemetry = any([
            payload.air_temperature is not None,
            payload.process_temperature is not None,
            payload.rotational_speed is not None,
            payload.torque is not None,
            payload.tool_wear is not None,
        ])
        
        if has_telemetry:
            # Save to machine_telemetry_logs table (historical record)
            telemetry_log = MachineTelemetry(
                machine_id=wo.machine_id,
                work_order_id=order_id,
                technician_id=current_user.id,
                air_temperature=payload.air_temperature or 0,
                process_temperature=payload.process_temperature or 0,
                rotational_speed=payload.rotational_speed or 0,
                torque=payload.torque or 0,
                tool_wear=payload.tool_wear or 0,
                recorded_at=now,
                notes=f"Work order #{order_id} completion"
            )
            db.add(telemetry_log)

        # ── Atomic parts consumption ──────────────────────────────────────
        if intervention and getattr(payload, "parts_consumed", None):
            try:
                reservation_svc = InventoryReservationService(db)
                for raw_item in payload.parts_consumed:
                    # Validate each item via Pydantic
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

        await db.commit()

        try:
            await AuditService(db).log_update(
                entity_type=AuditEntityType.WORK_ORDER,
                entity_id=order_id,
                old_values={"statut": "EN_COURS"},
                new_values={"statut": "TERMINÉ", "rapport": payload.rapport},
                user_id=current_user.id,
                user_name=current_user.nom,
            )
        except Exception:
            logger.warning("Audit log failed for complete work order %s", order_id)

        return {"message": "Work order completed", "statut": "TERMINÉ"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error completing work order: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
