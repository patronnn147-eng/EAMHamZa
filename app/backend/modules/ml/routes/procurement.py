"""P7 parts-demand: forecast, readiness/timeline, procurement queue + drafts, KPIs."""
from typing import Annotated, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_db
from models.machines import Machines
from models.utilisateurs import Utilisateurs

from .health import get_unified_health

router = APIRouter(tags=["Machine Learning"])


@router.get("/inventory/demand-forecast")
async def get_demand_forecast(
    *, horizon_days: Annotated[int, Query(
        ge=7,
        le=180,
        description="Only include machines failing within this many days",
    )] = 60,
    limit: Annotated[int, Query(ge=1, le=100, description="Max items to return")] = 20,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Dict:
    """
    Ranked spare parts reorder list based on RUL predictions x stock levels x consumption history.
    Cached 1 hour. Use POST /inventory/demand-forecast/refresh to bust.
    """
    from ..services.demand_forecast import compute_demand_forecast

    return await compute_demand_forecast(db, horizon_days=horizon_days, limit=limit)


@router.post("/inventory/demand-forecast/refresh")
async def refresh_demand_forecast():
    """Bust the demand forecast cache. Next GET will recompute."""
    from ..services.demand_forecast import invalidate_forecast_cache

    invalidate_forecast_cache()
    return {"status": "cache_cleared", "message": "Demand forecast cache cleared."}


@router.get("/machines/{machine_id}/readiness", responses={404: {"description": "Machine not found"}})
async def get_machine_readiness(
    machine_id: int, db: Annotated[AsyncSession, Depends(get_db)]
) -> Dict:
    """
    P7.5: 0-100 readiness score for a machine.
    Blends health score + inventory coverage + shortage risk + maintenance recency.
    """
    from modules.ml.services.readiness import get_readiness_for_machine

    # Re-use unified-health to get current score + parts_demand
    result = await db.execute(select(Machines).where(Machines.id == machine_id))
    machine = result.scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    # Last ML prediction log for health score proxy
    from models.ml_prediction_log import MlPredictionLog

    pred_q = await db.execute(
        select(MlPredictionLog)
        .where(MlPredictionLog.machine_id == machine_id)
        .order_by(MlPredictionLog.created_at.desc())
        .limit(1)
    )
    pred = pred_q.scalar_one_or_none()
    # health_score = invert failure_probability as rough proxy
    health_proxy = (
        max(0.0, 100.0 - (pred.failure_probability or 50.0)) if pred else 50.0
    )

    readiness = await get_readiness_for_machine(machine_id, health_proxy, None, db)
    return {"success": True, "machine_id": machine_id, **readiness}


@router.get("/machines/{machine_id}/timeline", responses={404: {"description": "Machine not found"}})
async def get_machine_timeline(
    *, machine_id: int,
    limit: int = 20,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Dict:
    """P7.5: Chronological maintenance event timeline for a machine."""
    from modules.ml.services.readiness import get_timeline_for_machine

    result = await db.execute(select(Machines).where(Machines.id == machine_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Machine not found")

    events = await get_timeline_for_machine(machine_id, db, limit=limit)
    return {
        "success": True,
        "machine_id": machine_id,
        "events": events,
        "count": len(events),
    }


@router.get("/kpis")
async def get_p7_kpis(db: Annotated[AsyncSession, Depends(get_db)]) -> Dict:
    """
    P7.5: Fleet-wide P7 KPIs derived from existing data.
    - stock_readiness_rate: % machines without active PARTS_SHORTAGE alert
    - adoption_rate: % machines with at least one ML prediction log
    - active_shortages: count of active PARTS_SHORTAGE alerts
    - draft_wos_pending: count of DRAFT work orders linked to P7 alerts
    """
    from models.alertes import Alert, AlertType
    from models.ml_prediction_log import MlPredictionLog
    from models.ordres_travail import OrdresTravail, OrdreStatut

    # Total machine count
    total_machines_q = await db.execute(select(func.count(Machines.id)))
    total_machines = total_machines_q.scalar() or 1  # avoid div-by-zero

    # Machines with active PARTS_SHORTAGE
    shortage_q = await db.execute(
        select(func.count(distinct(Alert.machine_id))).where(
            and_(Alert.alert_type == AlertType.PARTS_SHORTAGE, Alert.is_active)
        )
    )
    shortage_count = shortage_q.scalar() or 0

    # Machines with at least one prediction log
    pred_q = await db.execute(select(func.count(distinct(MlPredictionLog.machine_id))))
    predicted_machines = pred_q.scalar() or 0

    # Draft WOs pending approval
    draft_q = await db.execute(
        select(func.count(OrdresTravail.id)).where(
            OrdresTravail.statut == OrdreStatut.DRAFT
        )
    )
    draft_count = draft_q.scalar() or 0

    stock_readiness_rate = round(
        100.0 * (total_machines - shortage_count) / total_machines, 1
    )
    adoption_rate = round(100.0 * predicted_machines / total_machines, 1)

    return {
        "success": True,
        "kpis": {
            "stock_readiness_rate": stock_readiness_rate,
            "adoption_rate": adoption_rate,
            "active_shortages": shortage_count,
            "draft_wos_pending": draft_count,
            "total_machines": total_machines,
            "machines_with_predictions": predicted_machines,
        },
    }


@router.get("/procurement/queue")
async def get_procurement_queue(db: Annotated[AsyncSession, Depends(get_db)]) -> Dict:
    """
    P7: List machines with active PARTS_SHORTAGE alerts.
    Used by ADMIN procurement queue widget to review and act on shortfalls.
    Returns: [{machine_id, machine_name, severity, message, created_at}]
    """
    from models.alertes import Alert, AlertType

    result = await db.execute(
        select(Alert, Machines)
        .join(Machines, Alert.machine_id == Machines.id)
        .where(
            and_(
                Alert.alert_type == AlertType.PARTS_SHORTAGE,
                Alert.is_active,
            )
        )
        .order_by(Alert.created_at.desc())
    )
    rows = result.all()

    items = [
        {
            "alert_id": row.Alert.alert_id,
            "machine_id": row.Alert.machine_id,
            "machine_name": row.Machines.nom,
            "severity": row.Alert.severity.value,
            "message": row.Alert.message,
            "created_at": row.Alert.created_at.isoformat()
            if row.Alert.created_at
            else None,
        }
        for row in rows
    ]
    return {"success": True, "count": len(items), "items": items}


@router.post("/procurement/draft/{machine_id}", responses={404: {"description": "No active PARTS_SHORTAGE alert for this machine"}})
async def create_procurement_draft_endpoint(
    machine_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
) -> Dict:
    """
    P7.4: Create a DRAFT work order from the latest parts_demand shortfall
    for this machine. Deduped — one active draft per machine at a time.
    Human must approve before any reservation commits.
    """
    from modules.ml.services.parts_drafts import create_procurement_draft

    # Re-fetch parts_demand from the active PARTS_SHORTAGE alert's context.
    # Simplest approach: call unified-health and extract parts_demand.
    # For now, require caller to pass parts_demand in body or derive from alert.
    # We read the last alert message to confirm shortage exists.
    from models.alertes import Alert, AlertType

    alert_q = await db.execute(
        select(Alert).where(
            and_(
                Alert.machine_id == machine_id,
                Alert.alert_type == AlertType.PARTS_SHORTAGE,
                Alert.is_active,
            )
        )
    )
    alert = alert_q.scalar_one_or_none()
    if not alert:
        raise HTTPException(
            status_code=404, detail="No active PARTS_SHORTAGE alert for this machine"
        )

    if alert.work_order_id:
        return {
            "success": False,
            "message": "Draft already exists",
            "wo_id": alert.work_order_id,
        }

    # Build minimal parts_demand from alert message (real data comes at T26 persistence)
    # For now create draft with placeholder so the WO is created and linked
    placeholder_demand = {
        "horizon_days": 30,
        "source": "p7_model",
        "items": [
            {
                "piece_id": 0,
                "name": "see alert message",
                "expected_qty": 1.0,
                "on_hand": 0,
                "shortfall": 1.0,
                "driver": "condition",
            }
        ],
    }

    wo_id = await create_procurement_draft(
        machine_id=machine_id,
        parts_demand=placeholder_demand,
        created_by=current_user.id if current_user else None,
        db=db,
    )
    if wo_id is None:
        return {
            "success": False,
            "message": "Draft already exists or no items to draft",
        }
    await db.commit()
    return {
        "success": True,
        "wo_id": wo_id,
        "message": "Draft work order created — awaiting approval",
    }


@router.patch("/procurement/draft/{wo_id}/approve")
async def approve_procurement_draft_endpoint(
    wo_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
) -> Dict:
    """P7.4: Approve draft → SUBMITTED. Enters normal WO workflow."""
    from modules.ml.services.parts_drafts import approve_procurement_draft

    return await approve_procurement_draft(
        wo_id, current_user.id if current_user else 0, db
    )


@router.delete("/procurement/draft/{wo_id}")
async def reject_procurement_draft_endpoint(
    wo_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Dict:
    """P7.4: Reject/discard draft → ANNULÉ. Unlinks from PARTS_SHORTAGE alert."""
    from modules.ml.services.parts_drafts import reject_procurement_draft

    return await reject_procurement_draft(wo_id, db)


@router.post("/procurement/quick-action/{machine_id}", responses={403: {"description": "Only ADMIN can run Quick Action."}})
async def quick_action_endpoint(
    *, machine_id: int,
    dry_run: Annotated[bool, Query()] = False,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
) -> Dict:
    """
    Quick Action — ADMIN one-click: convert ML-recommended parts into real
    pieces + stock. Atomic, concurrency-safe, idempotent. `?dry_run=true`
    previews without writing.
    """
    # ADMIN guard (mirrors rag_docs._require_admin).
    role = (
        current_user.role.value
        if hasattr(current_user.role, "value")
        else str(current_user.role or "")
    ).upper()
    if role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only ADMIN can run Quick Action.")

    # Capture the actor id NOW — get_unified_health commits on this session, which
    # expires the current_user ORM object; reading current_user.id afterwards would
    # trigger a sync lazy-reload (MissingGreenlet) inside the async request.
    actor_user_id = current_user.id if current_user else None

    from modules.ml.services.quick_action import quick_provision_parts

    raw = await get_unified_health(machine_id, db)
    parts_demand = (raw or {}).get("parts_demand")

    return await quick_provision_parts(
        machine_id=machine_id,
        actor_user_id=actor_user_id,
        db=db,
        parts_demand=parts_demand,
        dry_run=dry_run,
    )
