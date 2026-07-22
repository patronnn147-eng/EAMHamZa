"""Unified-health endpoint: DST-fused health score + telemetry ingestion."""
from datetime import datetime, timedelta, timezone
from typing import Annotated, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import String, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.ml_client import is_ml_service_available, ml_client
from models.machines import Machines
from models.machine_telemetry import MachineTelemetry
from models.ordres_intervention import OrdresIntervention
from models.ordres_travail import OrdresTravail
from services.ai_prompts import build_sensor_status
from services.inventory.pieces import get_machine_parts_readiness

from ..rul_calculator import RULCalculator
from ._common import (
    _MACHINE_NOT_FOUND_MSG,
    _SYSTEM_TECHNICIAN_ID,
    _count_recent_interventions,
    _get_telemetry_history,
    _latest_sensors,
)

router = APIRouter(tags=["Machine Learning"])


class TelemetryUpdate(BaseModel):
    air_temperature: Optional[float] = None
    process_temperature: Optional[float] = None
    rotational_speed: Optional[int] = None
    torque: Optional[float] = None
    tool_wear: Optional[int] = None


def _build_uh_base_response(
    machine_id: int, machine, prediction: dict, fusion_result, sensors: tuple,
    telemetry_points: int = 0,
) -> dict:
    """Build the base unified-health response dict (no side-effect keys)."""
    _air, _proc, _rpm, _torq, _wear = sensors
    fr = fusion_result  # shorthand
    return {
        # Explicit data-availability contract: when telemetry_available is
        # false every sensor field is null and the ML models were not called —
        # the health figures come from the maintenance-history fallback only.
        "telemetry_available": telemetry_points > 0,
        "telemetry_data_points": telemetry_points,
        "machine_id": machine_id,
        "machine_name": machine.nom,
        "unified_health_score": prediction.get(
            "health_score", prediction.get("unified_health_score", 0.0)
        ),
        "score_source": prediction.get("health_breakdown", {}).get(
            "score_source", "fallback_additive"
        ),
        "dst_verdict": prediction.get("health_breakdown", {}).get("dst_verdict"),
        "conflict_factor_K": prediction.get("health_breakdown", {}).get("conflict_factor_K"),
        "kalman_hi": fr.get("kalman_hi") if fr else None,
        "kalman_rul": fr.get("kalman_rul") if fr else None,
        "sensor_fault_flag": fr.get("sensor_fault_flag", False) if fr else False,
        "model_outputs": fr.get("model_outputs") if fr else None,
        "rul_days": prediction.get("rul_days"),
        "failure_probability": prediction.get("failure_probability"),
        "risk_level": prediction.get("risk_level"),
        "health_score": prediction.get("health_score"),
        "health_breakdown": prediction.get("health_breakdown"),
        "reliability_score": prediction.get("reliability_score"),
        "explanations": prediction.get("explanations", []),
        "is_anomaly": prediction.get("is_anomaly", False),
        "p4_anomaly_score": fr.get("p4_anomaly_score", 0.0) if fr else 0.0,
        "predicted_priority": prediction.get("predicted_priority"),
        "air_temperature": _air,
        "process_temperature": _proc,
        "rotational_speed": _rpm,
        "torque": _torq,
        "tool_wear": int(_wear) if _wear is not None else None,
        "maintenance_event": fr.get("maintenance_event", False) if fr else False,
    }


async def _try_update_maintenance_schedule(machine, db: AsyncSession, schedule_days) -> Optional[float]:
    """Persist date_prochaine_maintenance and return rounded schedule days (non-fatal)."""
    rounded = round(schedule_days, 1) if schedule_days is not None else None
    if schedule_days and schedule_days > 0:
        try:
            base = machine.date_derniere_maintenance or datetime.now().astimezone()
            machine.date_prochaine_maintenance = base + timedelta(days=round(schedule_days))
            await db.commit()
        except Exception:
            pass  # never break the response
    return rounded


async def _enrich_parts_demand_with_real_stock(parts_demand: Dict, db: AsyncSession) -> Dict:
    """P7 fix: ml-microservice is stateless and has no DB access, so
    predict_parts_demand() computes shortfall/order/urgency against
    on_hand=0 for every part (parts_catalog is a static snapshot baked
    into the pkl at training time, not a live lookup — see p7_parts_demand.py
    build_parts_demand()). That makes every part with any expected demand
    look like a full shortfall, which is the mechanism behind P7's stale
    12% precision / 100% recall. Re-price each item here against the real,
    live Stock/Piece tables (the only place in the stack with DB access),
    using the same shortfall/order/urgency formula as build_parts_demand.
    """
    items = parts_demand.get("items") or []
    piece_ids = [i["piece_id"] for i in items if i.get("piece_id") is not None]
    if not piece_ids:
        return parts_demand

    from models.pieces import Piece
    from models.stock import Stock

    query = (
        select(Piece.id, Piece.name, Piece.reference, Piece.min_stock, Stock.quantity)
        .outerjoin(Stock, Stock.piece_id == Piece.id)
        .where(Piece.id.in_(piece_ids))
    )
    rows = (await db.execute(query)).all()
    real_stock = {
        row.id: {
            "name": row.name,
            "reference": row.reference,
            "min_stock": float(row.min_stock or 0),
            "on_hand": float(row.quantity or 0),
        }
        for row in rows
    }

    horizon = parts_demand.get("horizon_days") or 30

    for item in items:
        _reprice_part_item(item, real_stock, horizon)

    items.sort(key=lambda i: (-i["urgency_score"], -i["shortfall"]))
    parts_demand["items"] = items
    return parts_demand


def _reprice_part_item(item: Dict, real_stock: Dict, horizon: float) -> None:
    """Re-price one parts_demand item against real Stock/Piece data (mutates item in place)."""
    meta = real_stock.get(item["piece_id"])
    if not meta:
        return  # piece no longer catalogued — leave the pkl's stale numbers as-is
    expected = item.get("expected_qty", 0.0)
    on_hand = meta["on_hand"]
    min_stock = meta["min_stock"]
    shortfall = max(0.0, expected - on_hand)
    order = max(shortfall, min_stock - on_hand, 0.0)
    # Mirrors p7_parts_demand.py build_parts_demand()/stock_coverage_days
    # exactly — this function re-prices items after the ml-microservice
    # call. stock_coverage_days is display-only (see the NOTE in that
    # file): algebraically identical to shortfall/expected whenever
    # shortfall>0, so it's computed here purely for display consistency,
    # not used to adjust urgency_score.
    daily_burn = expected / horizon if horizon else 0.0
    coverage = (on_hand / daily_burn) if daily_burn > 0 else None
    urgency = round(min(1.0, (shortfall / expected) if expected else 0.0), 4)
    item["on_hand"] = on_hand
    item["min_stock"] = int(min_stock)
    item["shortfall"] = round(shortfall, 3)
    item["recommended_order_qty"] = round(order, 3)
    item["stock_coverage_days"] = round(coverage, 1) if coverage is not None else None
    item["urgency_score"] = urgency
    if meta["name"]:
        item["name"] = meta["name"]
    if meta["reference"]:
        item["reference"] = meta["reference"]


@router.get("/machines/{machine_id}/unified-health", responses={404: {"description": "Machine non trouvée"}})
async def get_unified_health(
    machine_id: int, db: Annotated[AsyncSession, Depends(get_db)]
) -> Dict:
    """
    Get the DST-fused unified health score for a machine.

    This endpoint resolves the dual-score contradiction (rule-based 92/100 vs
    ML-based 0/100) by fusing all model signals through Dempster-Shafer Evidence
    Theory + Kalman smoothing into a single authoritative health verdict.

    Response:
        unified_health_score: float [0-100] â the single authoritative score
        score_source: "dst_fusion" | "fallback_additive"
        dst_verdict: "Healthy" | "Degrading" | "Critical" | "Unknown"
        conflict_factor_K: float [0-1] â model agreement (< 0.8 = good)
        kalman_hi: float â Kalman-smoothed health index
        kalman_rul: float â Kalman-smoothed RUL estimate (days)
        model_outputs: per-model health indices
        rul_days, failure_probability, risk_level â standard prediction fields
        maintenance_event: bool â true when tool_wear reset detected (Mahal excluded from DST)
    """
    machine = await _fetch_machine_or_404(machine_id, db)

    execute_result = await db.execute(
        select(OrdresIntervention).where(OrdresIntervention.machine_id == machine_id)
    )
    interventions = list(execute_result.scalars().all())

    open_wo_count = await _count_open_work_orders(machine_id, db)

    now_dt = datetime.now(timezone.utc)
    recent_count = _count_recent_interventions(interventions, now_dt - timedelta(days=30))

    telemetry_entries, telemetry_logs = await _get_telemetry_history(machine_id, db)

    # No telemetry => no sensor values. We never substitute placeholder
    # readings: fabricated inputs produce identical, meaningless predictions
    # for every machine while looking like a healthy pipeline.
    sensors = _latest_sensors(telemetry_entries)

    fusion_result = await _run_ml_fusion(telemetry_entries, telemetry_logs, sensors, machine_id)

    prediction = RULCalculator.calculate_rul(
        machine,
        interventions,
        telemetry_entries=telemetry_entries,
        open_work_orders=open_wo_count,
        recent_interventions=recent_count,
        fusion_result=fusion_result,
    )

    response = _build_uh_base_response(
        machine_id, machine, prediction, fusion_result, sensors,
        telemetry_points=len(telemetry_entries),
    )

    await _attach_parts_and_schedule(response, machine, fusion_result, machine_id, db)
    await _attach_recovery(response, machine_id, db)
    _attach_sensor_status(response, machine)

    return response


async def _fetch_machine_or_404(machine_id: int, db: AsyncSession) -> Machines:
    result = await db.execute(select(Machines).where(Machines.id == machine_id))
    machine = result.scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail=_MACHINE_NOT_FOUND_MSG)
    return machine


async def _count_open_work_orders(machine_id: int, db: AsyncSession) -> int:
    from sqlalchemy import func as sa_func

    wo_result = await db.execute(
        select(sa_func.count(OrdresTravail.id)).where(
            OrdresTravail.machine_id == machine_id,
            cast(OrdresTravail.statut, String).notin_(
                ["CLOSED", "VALIDATED", "REJECTED", "ANNULÉ"]
            ),
        )
    )
    return wo_result.scalar() or 0


async def _run_ml_fusion(telemetry_entries, telemetry_logs, sensors: tuple, machine_id: int) -> Optional[Dict]:
    _air, _proc, _rpm, _torq, _wear = sensors
    try:
        if telemetry_entries and await is_ml_service_available():
            return await ml_client.predict_all(
                air_temperature=_air,
                process_temperature=_proc,
                rotational_speed=_rpm,
                torque=_torq,
                tool_wear=int(_wear),
                machine_id=machine_id,
                telemetry_logs=telemetry_logs,
                include_shap=True,
            )
    except Exception:
        pass
    return None


async def _attach_parts_and_schedule(
    response: Dict, machine, fusion_result: Optional[Dict], machine_id: int, db: AsyncSession
) -> None:
    try:
        parts_readiness = await get_machine_parts_readiness(machine_id, db)
    except Exception:
        parts_readiness = {"status": "UNKNOWN", "error": "inventory_unavailable"}
    response["parts_readiness"] = parts_readiness

    _schedule_days = fusion_result.get("p6_schedule_days") if fusion_result else None
    response["p6_schedule_days"] = await _try_update_maintenance_schedule(
        machine, db, _schedule_days
    )

    _parts_demand = fusion_result.get("p7_parts_demand") if fusion_result else None
    if _parts_demand:
        _parts_demand = await _enrich_parts_demand_with_real_stock(_parts_demand, db)
    response["parts_demand"] = _parts_demand

    try:
        from modules.ml.services.parts_alerts import emit_shortfall_alert

        await emit_shortfall_alert(machine_id, _parts_demand, db)
    except Exception:
        pass


async def _attach_recovery(response: Dict, machine_id: int, db: AsyncSession) -> None:
    try:
        from services.ml.recovery import PostMaintenanceRecoveryService

        recovery = await PostMaintenanceRecoveryService(db).get_latest_recovery_for_machine(
            machine_id=machine_id,
            current_score=response.get("unified_health_score"),
        )
        response["recovery"] = recovery.to_dict() if recovery is not None else None
    except Exception:
        response["recovery"] = None


def _attach_sensor_status(response: Dict, machine) -> None:
    try:
        if not response["telemetry_available"]:
            raise ValueError("no telemetry")  # no readings => no per-sensor status
        response["sensor_status"] = build_sensor_status(
            machine.type or "",
            machine.nom or "",
            {
                "air_temperature": response.get("air_temperature"),
                "process_temperature": response.get("process_temperature"),
                "rotational_speed": response.get("rotational_speed"),
                "torque": response.get("torque"),
                "tool_wear": response.get("tool_wear"),
            },
        )
    except Exception:
        response["sensor_status"] = []


@router.patch("/machines/{machine_id}/telemetry", responses={404: {"description": "Machine non trouvée"}})
async def update_machine_telemetry(
    machine_id: int,
    data: TelemetryUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Dict:
    """
    Insert a manual telemetry entry for a machine (simulation / testing).
    Writes to machine_telemetry_logs so the ML pipeline picks it up.
    """
    result = await db.execute(select(Machines).where(Machines.id == machine_id))
    machine = result.scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail=_MACHINE_NOT_FOUND_MSG)

    entry = MachineTelemetry(
        machine_id=machine_id,
        work_order_id=None,
        technician_id=_SYSTEM_TECHNICIAN_ID,  # configurable via SYSTEM_TECHNICIAN_ID env var
        air_temperature=data.air_temperature or 300.0,
        process_temperature=data.process_temperature or 310.0,
        rotational_speed=data.rotational_speed or 1500,
        torque=data.torque or 40.0,
        tool_wear=data.tool_wear or 0.0,
        recorded_at=datetime.now(timezone.utc),
        notes="Manual simulation entry",
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    return {
        "message": "Telemetry entry recorded",
        "machine_id": machine_id,
        "telemetry": {
            "air_temperature": entry.air_temperature,
            "process_temperature": entry.process_temperature,
            "rotational_speed": entry.rotational_speed,
            "torque": entry.torque,
            "tool_wear": entry.tool_wear,
        },
    }
