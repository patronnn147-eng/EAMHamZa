from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, asc, cast, String
from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs
from models.machines import Machines
from models.ordres_intervention import Ordres_intervention
from models.ordres_travail import Ordres_travail, OrdreStatut
from models.ml_prediction_log import MlPredictionLog
from models.machine_telemetry import MachineTelemetry
from .logging import ShadowLogger
from .rul_calculator import RULCalculator
from .services.ml_retraining import RetrainingService
from core.ml_client import ml_client, is_ml_service_available, get_model_metrics
from services.inventory.pieces import batch_get_parts_readiness, get_machine_parts_readiness
from services.ai_prompts import build_sensor_status

from pydantic import BaseModel
from typing import Dict, List, Optional
from schemas.pagination import PaginatedResponse
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from pathlib import Path as _Path
import asyncio
import os

# System/simulation entries need a non-null technician_id.
# Set SYSTEM_TECHNICIAN_ID env var to a valid technician PK in your DB.
# Default 0 works when there is no FK constraint on technician_id.
_SYSTEM_TECHNICIAN_ID = int(os.getenv("SYSTEM_TECHNICIAN_ID", "0"))

_BACKEND_MODELS = str(_Path(__file__).parent / "models")
_MICRO_MODELS = str(_Path(__file__).resolve().parents[3] / "ml-microservice" / "models")

router = APIRouter(prefix="/api/v1/ml", tags=["Machine Learning"])

# Simple in-memory cache for fleet dashboard
_fleet_cache = {
    "data": None,
    "timestamp": None,
    "ttl_seconds": 300  # 5 minutes cache
}


class TelemetryUpdate(BaseModel):
    air_temperature: Optional[float] = None
    process_temperature: Optional[float] = None
    rotational_speed: Optional[int] = None
    torque: Optional[float] = None
    tool_wear: Optional[int] = None



async def _get_telemetry_history(machine_id: int, db: AsyncSession):
    """
    Query all telemetry entries for a machine ordered oldest-first.
    Returns (entries, log_dicts) where log_dicts is compatible with
    FeatureStore.build_time_series_from_logs.
    """
    # Fetch latest 500 entries (matches microservice _MAX_LOGS cap).
    # Order DESC + limit, then reverse in Python to get oldest-first ascending.
    result = await db.execute(
        select(MachineTelemetry)
        .where(MachineTelemetry.machine_id == machine_id)
        .order_by(MachineTelemetry.recorded_at.desc())
        .limit(500)
    )
    entries = list(reversed(result.scalars().all()))
    log_dicts = [
        {
            "machine_id":           machine_id,
            "air_temperature":      e.air_temperature,
            "process_temperature":  e.process_temperature,
            "rotational_speed":     e.rotational_speed,
            "torque":               e.torque,
            "tool_wear":            e.tool_wear,
            "created_at":           e.recorded_at.isoformat() if e.recorded_at else "",
            "risk_level":           "LOW",
        }
        for e in entries
    ]
    return entries, log_dicts


@router.get("/machines/{machine_id}/unified-health")
async def get_unified_health(machine_id: int, db: AsyncSession = Depends(get_db)) -> Dict:
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
    result = await db.execute(select(Machines).where(Machines.id == machine_id))
    machine = result.scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine non trouvée")

    interventions_query = select(Ordres_intervention).where(
        Ordres_intervention.machine_id == machine_id
    )
    execute_result = await db.execute(interventions_query)
    interventions = list(execute_result.scalars().all())

    from sqlalchemy import func as sa_func
    wo_query = select(sa_func.count(Ordres_travail.id)).where(
        Ordres_travail.machine_id == machine_id,
        cast(Ordres_travail.statut, String).notin_(["CLOSED", "VALIDATED", "REJECTED", "ANNULÉ"])
    )
    wo_result = await db.execute(wo_query)
    open_wo_count = wo_result.scalar() or 0

    from datetime import datetime, timedelta, timezone
    now_dt = datetime.now(timezone.utc)
    thirty_days_ago = now_dt - timedelta(days=30)
    recent_count = len([
        i for i in interventions
        if i.date_intervention and (
            i.date_intervention.replace(tzinfo=timezone.utc)
            if i.date_intervention.tzinfo is None else i.date_intervention
        ) > thirty_days_ago
    ])

    # Query telemetry history; derive scalars from latest entry or use defaults
    telemetry_entries, telemetry_logs = await _get_telemetry_history(machine_id, db)

    if telemetry_entries:
        latest = telemetry_entries[-1]
        _air   = float(latest.air_temperature)
        _proc  = float(latest.process_temperature)
        _rpm   = int(latest.rotational_speed)
        _torq  = float(latest.torque)
        _wear  = float(latest.tool_wear)
    else:
        _air, _proc, _rpm, _torq, _wear = 300.0, 310.0, 1500, 40.0, 0.0

    # Try ML microservice for DST fusion.
    # include_shap=True: unified-health is the detailed view and needs explanations.
    fusion_result: Optional[Dict] = None
    try:
        if await is_ml_service_available():
            fusion_result = await ml_client.predict_all(
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

    prediction = RULCalculator.calculate_rul(
        machine,
        interventions,
        telemetry_entries=telemetry_entries,
        open_work_orders=open_wo_count,
        recent_interventions=recent_count,
        fusion_result=fusion_result,
    )

    # Build unified-health response shape (superset of /prediction)
    response = {
        "machine_id": machine_id,
        "machine_name": machine.nom,
        "unified_health_score": prediction.get(
            "health_score",
            prediction.get("unified_health_score", 0.0)
        ),
        "score_source": prediction.get("health_breakdown", {}).get("score_source", "fallback_additive"),
        "dst_verdict": prediction.get("health_breakdown", {}).get("dst_verdict"),
        "conflict_factor_K": prediction.get("health_breakdown", {}).get("conflict_factor_K"),
        "kalman_hi": fusion_result.get("kalman_hi") if fusion_result else None,
        "kalman_rul": fusion_result.get("kalman_rul") if fusion_result else None,
        "sensor_fault_flag": fusion_result.get("sensor_fault_flag", False) if fusion_result else False,
        "model_outputs": fusion_result.get("model_outputs") if fusion_result else None,
        "rul_days": prediction.get("rul_days"),
        "failure_probability": prediction.get("failure_probability"),
        "risk_level": prediction.get("risk_level"),
        "health_score": prediction.get("health_score"),
        "health_breakdown": prediction.get("health_breakdown"),
        "reliability_score": prediction.get("reliability_score"),
        "explanations": prediction.get("explanations", []),
        "is_anomaly": prediction.get("is_anomaly", False),
        "p4_anomaly_score": fusion_result.get("p4_anomaly_score", 0.0) if fusion_result else 0.0,
        "predicted_priority": prediction.get("predicted_priority"),
        # Latest telemetry readings
        "air_temperature": _air,
        "process_temperature": _proc,
        "rotational_speed": _rpm,
        "torque": _torq,
        "tool_wear": int(_wear),
        # maintenance_event: true when tool_wear reset detected — Mahal excluded from DST that step
        "maintenance_event": fusion_result.get("maintenance_event", False) if fusion_result else False,
    }

    # Inventory: parts availability for this machine
    try:
        parts_readiness = await get_machine_parts_readiness(machine_id, db)
    except Exception:
        parts_readiness = {"status": "UNKNOWN", "error": "inventory_unavailable"}
    response["parts_readiness"] = parts_readiness

    # P6: maintenance schedule (days until next recommended maintenance)
    _schedule_days = fusion_result.get("p6_schedule_days") if fusion_result else None
    response["p6_schedule_days"] = round(_schedule_days, 1) if _schedule_days is not None else None

    # Side-effect: persist date_prochaine_maintenance on every ML call
    if _schedule_days and _schedule_days > 0:
        try:
            base = machine.date_derniere_maintenance or datetime.now().astimezone()
            machine.date_prochaine_maintenance = base + timedelta(days=round(_schedule_days))
            await db.commit()
        except Exception:
            pass  # never break the response

    # P7: condition-aware parts demand forecast (from ml-microservice predict_all)
    _parts_demand = fusion_result.get("p7_parts_demand") if fusion_result else None
    response["parts_demand"] = _parts_demand

    # P7: emit PARTS_SHORTAGE alert if shortfall detected (non-fatal, deduped)
    try:
        from modules.ml.services.parts_alerts import emit_shortfall_alert
        await emit_shortfall_alert(machine_id, _parts_demand, db)
    except Exception:
        pass  # alert failure never breaks the response

    # Post-maintenance recovery: compare current unified_health_score against
    # the snapshot taken at the most recent work order's creation.
    try:
        from services.ml.recovery import PostMaintenanceRecoveryService
        recovery = await PostMaintenanceRecoveryService(db).get_latest_recovery_for_machine(
            machine_id=machine_id,
            current_score=response.get("unified_health_score"),
        )
        response["recovery"] = recovery.to_dict() if recovery is not None else None
    except Exception:
        response["recovery"] = None

    # Sensor status — best-effort, never raises
    try:
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

    return response


@router.get("/machines/{machine_id}/prediction")
async def get_machine_prediction(machine_id: int, db: AsyncSession = Depends(get_db)) -> Dict:
    """
    Get ML-based predictive maintenance data for a specific machine.
    Uses intervention history + the trained .pkl model to estimate:
      - rul_days: estimated days before failure
      - risk_level: LOW / MEDIUM / HIGH / CRITICAL
      - failure_probability: 0-100 (blended from model + MTBF)
      - predicted_failure_date: ISO timestamp
    Also logs the prediction to ml_prediction_logs (PDCA Shadow Logging).
    """
    # 1. Fetch machine
    result = await db.execute(select(Machines).where(Machines.id == machine_id))
    machine = result.scalar_one_or_none()

    if not machine:
        raise HTTPException(status_code=404, detail="Machine non trouvée")

    # 2. Fetch intervention history for this machine
    interventions_query = select(Ordres_intervention).where(
        Ordres_intervention.machine_id == machine_id
    )
    execute_result = await db.execute(interventions_query)
    interventions = list(execute_result.scalars().all())

    # 3. Fetch count of open work orders (Ordres de travail)
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import func
    now_dt = datetime.now(timezone.utc)

    # Open = not TERMINÉ or ANNULÉ
    wo_query = select(func.count(Ordres_travail.id)).where(
        Ordres_travail.machine_id == machine_id,
        cast(Ordres_travail.statut, String).notin_(["CLOSED", "VALIDATED", "REJECTED", "ANNULÉ"])
    )
    wo_result = await db.execute(wo_query)
    open_wo_count = wo_result.scalar() or 0

    # 4. Count recent interventions (last 30 days)
    thirty_days_ago = now_dt - timedelta(days=30)
    recent_interventions_count = len([
        i for i in interventions
        if i.date_intervention and (
            i.date_intervention.replace(tzinfo=timezone.utc) if i.date_intervention.tzinfo is None else i.date_intervention
        ) > thirty_days_ago
    ])

    # 5. Query telemetry history; derive scalars from latest entry or use defaults
    telemetry_entries, telemetry_logs = await _get_telemetry_history(machine_id, db)

    if telemetry_entries:
        latest = telemetry_entries[-1]
        _air   = float(latest.air_temperature)
        _proc  = float(latest.process_temperature)
        _rpm   = int(latest.rotational_speed)
        _torq  = float(latest.torque)
        _wear  = float(latest.tool_wear)
    else:
        _air, _proc, _rpm, _torq, _wear = 300.0, 310.0, 1500, 40.0, 0.0

    # 6. Optionally fetch DST fusion from ML microservice (best-effort, non-blocking)
    fusion_result: Optional[Dict] = None
    try:
        if await is_ml_service_available():
            fusion_result = await ml_client.predict_all(
                air_temperature=_air,
                process_temperature=_proc,
                rotational_speed=_rpm,
                torque=_torq,
                tool_wear=int(_wear),
                machine_id=machine_id,
                telemetry_logs=telemetry_logs,
            )
    except Exception:
        pass  # ML microservice unavailable — rul_calculator uses fallback formula

    # 7. Calculate prediction with unified health
    try:
        prediction = RULCalculator.calculate_rul(
            machine,
            interventions,
            telemetry_entries=telemetry_entries,
            open_work_orders=open_wo_count,
            recent_interventions=recent_interventions_count,
            fusion_result=fusion_result,
        )

        # 4. Shadow Log (PDCA Phase 1): persist prediction without showing to user
        try:
            log_entry = ShadowLogger.create_shadow_log(prediction)
            db.add(log_entry)
            await db.commit()
        except Exception:
            await db.rollback()  # Don't fail the prediction if logging fails

        return prediction
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"ML Calculation Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors du calcul ML: {str(e)}")


@router.get("/machines/{machine_id}/failure-probability")
async def get_failure_probability(
    machine_id: int,
    air: float = Query(..., description="Air temperature [K]"),
    process: float = Query(..., description="Process temperature [K]"),
    rpm: int = Query(..., description="Rotational speed [rpm]"),
    torque: float = Query(..., description="Torque [Nm]"),
    wear: int = Query(..., description="Tool wear [min]"),
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    Return failure probability for a machine using the trained ML model (P1).

    Feature order matches training data: [air, process, rpm, torque, wear]

    Returns:
        machine_id: int
        failure_probability: float (0-100)
        risk_level: "LOW_RISK" | "HIGH_RISK"
    """
    result = await db.execute(select(Machines).where(Machines.id == machine_id))
    machine = result.scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine non trouvée")

    # Delegate to ML microservice
    try:
        ml_result = await ml_client.predict_failure_probability(
            air_temperature=air,
            process_temperature=process,
            rotational_speed=rpm,
            torque=torque,
            tool_wear=wear,
        )
        probability = float(ml_result.get("failure_probability", ml_result.get("prediction", {}).get("failure_probability", 0.0)))
    except Exception:
        probability = 0.0

    return {
        "machine_id": machine_id,
        "machine_name": machine.nom,
        "failure_probability": probability,
        "risk_level": "HIGH_RISK" if probability > 50 else "LOW_RISK",
    }


@router.get("/machines/{machine_id}/failure-type")
async def get_failure_type(
    machine_id: int,
    air: float = Query(..., description="Air temperature [K]"),
    process: float = Query(..., description="Process temperature [K]"),
    rpm: int = Query(..., description="Rotational speed [rpm]"),
    torque: float = Query(..., description="Torque [Nm]"),
    wear: int = Query(..., description="Tool wear [min]"),
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    Predict specific failure types for a machine (P2).
    Returns binary detection and probability for each type:
    TWF, HDF, PWF, OSF, RNF
    """
    result = await db.execute(select(Machines).where(Machines.id == machine_id))
    machine = result.scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine non trouvée")

    # Features: [air, process, rpm, torque, wear, temp_delta]
    temp_delta = process - air
    features = [float(air), float(process), float(rpm), float(torque), float(wear), float(temp_delta)]

    # Delegate to ML microservice
    try:
        ml_result = await ml_client.predict_failure_type(
            air_temperature=air,
            process_temperature=process,
            rotational_speed=rpm,
            torque=torque,
            tool_wear=wear,
        )
        failure_types = ml_result.get("failure_types", {})
    except Exception:
        failure_types = {}

    return {
        "machine_id": machine_id,
        "machine_name": machine.nom,
        "failure_types": failure_types
    }


@router.get("/fleet/critical")
async def get_fleet_critical_predictions(db: AsyncSession = Depends(get_db)):
    """
    Get machines with the highest risk of failure across the fleet.
    Returns only HIGH and CRITICAL risk machines, sorted by rul_days ascending.
    """
    result = await db.execute(select(Machines))
    machines = result.scalars().all()
    predictions = []

    # Single query for all interventions — avoids N per-machine round-trips.
    all_oi_result = await db.execute(select(Ordres_intervention))
    _oi_by_machine: dict = {}
    for _oi in all_oi_result.scalars().all():
        _oi_by_machine.setdefault(_oi.machine_id, []).append(_oi)

    for machine in machines:
        interventions = _oi_by_machine.get(machine.id, [])
        pred = RULCalculator.calculate_rul(machine, list(interventions))
        if pred["risk_level"] in ["CRITICAL", "HIGH"]:
            predictions.append(pred)

    return {"machines": sorted(predictions, key=lambda x: x["rul_days"])}


async def _process_single_machine(
    machine: Machines,
    db: AsyncSession,
    interventions_by_machine: dict = None,
    latest_logs_by_machine: dict = None,
    latest_telemetry_by_machine: dict = None,
    parts_readiness_map: dict = None,
) -> Dict:
    """Helper to process single machine prediction.

    Args:
        interventions_by_machine: pre-fetched dict {machine_id: [Ordres_intervention]}
        latest_logs_by_machine: pre-fetched dict {machine_id: MlPredictionLog} — latest log row per machine
        latest_telemetry_by_machine: pre-fetched dict {machine_id: MachineTelemetry} -- latest telemetry row per machine
        parts_readiness_map: pre-fetched dict {machine_id: status} -- inventory readiness per machine
    """
    if interventions_by_machine is not None:
        interventions = interventions_by_machine.get(machine.id, [])
    else:
        execute_result = await db.execute(
            select(Ordres_intervention).where(Ordres_intervention.machine_id == machine.id)
        )
        interventions = execute_result.scalars().all()

    # Build synthetic fusion_result from latest MlPredictionLog row.
    # Avoids per-machine ML microservice calls while giving realistic health scores.
    # RULCalculator uses failure_probability — health = 100 - failure_prob.
    fusion_result = None
    if latest_logs_by_machine is not None:
        log = latest_logs_by_machine.get(machine.id)
        if log is not None:
            fusion_result = {
                "p1_failure_probability": float(log.failure_probability or 0.0),
                "p3_rul_days":           float(log.rul_days) if log.rul_days is not None else None,
                "p4_is_anomaly":         bool(log.is_anomaly or False),
                "p4_anomaly_score":      float(log.anomaly_score or 0.0),
                "p5_predicted_priority": log.predicted_priority,
                "p2_failure_types":      {},
            }

    # Build telemetry_entries list from latest snapshot (for degradation rate).
    telemetry_entries = []
    if latest_telemetry_by_machine is not None:
        entry = latest_telemetry_by_machine.get(machine.id)
        if entry is not None:
            telemetry_entries = [entry]

    pred = RULCalculator.calculate_rul(
        machine,
        list(interventions),
        telemetry_entries=telemetry_entries if telemetry_entries else None,
        fusion_result=fusion_result,
    )
    pred["zone"] = machine.zone
    pred["sous_zone"] = machine.sous_zone
    pred["statut"] = machine.statut
    pred["parts_ready"] = (parts_readiness_map or {}).get(machine.id, "OK")
    return pred


@router.get("/fleet/dashboard")
async def get_fleet_dashboard(db: AsyncSession = Depends(get_db)):
    """
    PDCA Fleet Dashboard: Full overview of ALL machines with ML predictions.
    Cached for 5 minutes + parallel processing for speed.
    """
    now = datetime.utcnow()

    # Check cache
    if (_fleet_cache["data"] is not None and
        _fleet_cache["timestamp"] is not None and
        (now - _fleet_cache["timestamp"]).total_seconds() < _fleet_cache["ttl_seconds"]):
        return _fleet_cache["data"]

    # Build dashboard fresh - parallel processing
    result = await db.execute(select(Machines))
    machines = result.scalars().all()

    # Fetch ALL interventions in a single query and group by machine_id.
    # Avoids N per-machine queries (was O(N) DB round-trips, now O(1)).
    all_interventions_result = await db.execute(select(Ordres_intervention))
    _interventions_by_machine: dict = {}
    for _oi in all_interventions_result.scalars().all():
        _interventions_by_machine.setdefault(_oi.machine_id, []).append(_oi)

    # Batch-fetch latest MlPredictionLog per machine (one query, no ML calls).
    # Subquery: for each machine_id, get the id of the most recent log row.
    from sqlalchemy import func as sa_func
    latest_log_subq = (
        select(
            MlPredictionLog.machine_id,
            sa_func.max(MlPredictionLog.id).label("max_id"),
        )
        .group_by(MlPredictionLog.machine_id)
        .subquery()
    )
    _latest_logs_result = await db.execute(
        select(MlPredictionLog).join(
            latest_log_subq,
            (MlPredictionLog.machine_id == latest_log_subq.c.machine_id)
            & (MlPredictionLog.id == latest_log_subq.c.max_id),
        )
    )
    _latest_logs_by_machine: dict = {
        row.machine_id: row for row in _latest_logs_result.scalars().all()
    }

    # Batch-fetch latest MachineTelemetry per machine.
    latest_telem_subq = (
        select(
            MachineTelemetry.machine_id,
            sa_func.max(MachineTelemetry.id).label("max_id"),
        )
        .group_by(MachineTelemetry.machine_id)
        .subquery()
    )
    _latest_telem_result = await db.execute(
        select(MachineTelemetry).join(
            latest_telem_subq,
            (MachineTelemetry.machine_id == latest_telem_subq.c.machine_id)
            & (MachineTelemetry.id == latest_telem_subq.c.max_id),
        )
    )
    _latest_telem_by_machine: dict = {
        row.machine_id: row for row in _latest_telem_result.scalars().all()
    }

    # Batch-fetch inventory parts readiness for all machines (single query).
    try:
        _parts_readiness_map = await batch_get_parts_readiness(db)
    except Exception:
        _parts_readiness_map = {}

    # Process all machines in parallel
    tasks = [
        _process_single_machine(
            m, db,
            _interventions_by_machine,
            _latest_logs_by_machine,
            _latest_telem_by_machine,
            _parts_readiness_map,
        )
        for m in machines
    ]
    dashboard = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out errors
    dashboard = [d for d in dashboard if isinstance(d, dict)]

    # Sort: CRITICAL first, then HIGH, then MEDIUM, then LOW
    risk_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    sorted_dashboard = sorted(dashboard, key=lambda x: (risk_order.get(x["risk_level"], 4), x["rul_days"]))

    # Cache result
    _fleet_cache["data"] = sorted_dashboard
    _fleet_cache["timestamp"] = now

    return sorted_dashboard


@router.post("/fleet/dashboard/refresh")
async def refresh_fleet_dashboard():
    """Force refresh the fleet dashboard cache."""
    _fleet_cache["data"] = None
    _fleet_cache["timestamp"] = None
    return {"status": "cache_cleared", "message": "Dashboard cache cleared. Next request will rebuild."}


@router.get("/inventory/demand-forecast")
async def get_demand_forecast(
    horizon_days: int = Query(60, ge=7, le=180, description="Only include machines failing within this many days"),
    limit: int = Query(20, ge=1, le=100, description="Max items to return"),
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    Ranked spare parts reorder list based on RUL predictions x stock levels x consumption history.
    Cached 1 hour. Use POST /inventory/demand-forecast/refresh to bust.
    """
    from .services.demand_forecast import compute_demand_forecast
    return await compute_demand_forecast(db, horizon_days=horizon_days, limit=limit)


@router.post("/inventory/demand-forecast/refresh")
async def refresh_demand_forecast():
    """Bust the demand forecast cache. Next GET will recompute."""
    from .services.demand_forecast import invalidate_forecast_cache
    invalidate_forecast_cache()
    return {"status": "cache_cleared", "message": "Demand forecast cache cleared."}


@router.get("/shadow-logs")
async def get_shadow_logs(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(100, ge=1, le=1000, description="Items per page"),
    machine_id: int = Query(None, description="Filter by machine ID"),
    risk_level: str = Query(None, description="Filter by risk level (CRITICAL, HIGH, MEDIUM, LOW)"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[Dict]:
    """
    PDCA Audit: Retrieve shadow-logged ML predictions.
    Used by managers to compare predictions against actual outcomes.
    """
    query = select(MlPredictionLog)
    count_query = select(func.count()).select_from(MlPredictionLog)

    if machine_id is not None:
        query = query.where(MlPredictionLog.machine_id == machine_id)
        count_query = count_query.where(MlPredictionLog.machine_id == machine_id)
    if risk_level is not None:
        query = query.where(MlPredictionLog.risk_level == risk_level)
        count_query = count_query.where(MlPredictionLog.risk_level == risk_level)

    total_result = await db.execute(count_query)
    total_count = total_result.scalar_one()

    skip = (page - 1) * size
    query = query.order_by(desc(MlPredictionLog.created_at)).offset(skip).limit(size)

    result = await db.execute(query)
    logs = result.scalars().all()

    items = [
        {
            "id": log.id,
            "machine_id": log.machine_id,
            "machine_name": log.machine_name,
            "risk_level": log.risk_level,
            "failure_probability": log.failure_probability,
            "rul_days": log.rul_days,
            "predicted_failure_date": log.predicted_failure_date,
            "predicted_priority": log.predicted_priority,
            "is_anomaly": log.is_anomaly,
            "anomaly_score": log.anomaly_score,
            "data_points": log.data_points,
            "ml_model_used": log.ml_model_used,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]

    return PaginatedResponse.create(items=items, total=total_count, page=page, size=size)


@router.patch("/machines/{machine_id}/telemetry")
async def update_machine_telemetry(
    machine_id: int,
    data: TelemetryUpdate,
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    Insert a manual telemetry entry for a machine (simulation / testing).
    Writes to machine_telemetry_logs so the ML pipeline picks it up.
    """
    result = await db.execute(select(Machines).where(Machines.id == machine_id))
    machine = result.scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine non trouvée")

    entry = MachineTelemetry(
        machine_id=machine_id,
        work_order_id=None,
        technician_id=_SYSTEM_TECHNICIAN_ID,  # configurable via SYSTEM_TECHNICIAN_ID env var
        air_temperature=data.air_temperature or 300.0,
        process_temperature=data.process_temperature or 310.0,
        rotational_speed=data.rotational_speed or 1500,
        torque=data.torque or 40.0,
        tool_wear=data.tool_wear or 0.0,
        recorded_at=datetime.utcnow(),
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


@router.get("/retrain/stats")
async def get_retraining_stats(db: AsyncSession = Depends(get_db)) -> Dict:
    """
    Get statistics on new ground truth data available for retraining.
    Used by the ML Admin Dashboard.
    """
    return await RetrainingService.get_retraining_stats(db)


@router.post("/retrain")
async def trigger_retraining(
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    """
    Manually trigger the PDCA Act Phase: automated retraining. ADMIN only.
    Accepts optional JSON body {"model_type": "all"}.
    """
    _require_admin(current_user)
    try:
        result = await RetrainingService.run_retraining_pipeline(db)
        return result if result is not None else {"status": "success", "message": "Retraining pipeline completed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def ml_service_status():
    """
    Check ML container status.
    Returns whether the ML microservice is available.
    """
    available = await is_ml_service_available()
    return {
        "ml_service_available": available,
        "ml_service_url": "http://ml-service:8000",
        "fallback": "Local calculation" if not available else "ML Container"
    }


@router.get("/machines/{machine_id}/readiness")
async def get_machine_readiness(machine_id: int, db: AsyncSession = Depends(get_db)) -> Dict:
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
    health_proxy = max(0.0, 100.0 - (pred.failure_probability or 50.0)) if pred else 50.0

    readiness = await get_readiness_for_machine(machine_id, health_proxy, None, db)
    return {"success": True, "machine_id": machine_id, **readiness}


@router.get("/machines/{machine_id}/timeline")
async def get_machine_timeline(
    machine_id: int,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """P7.5: Chronological maintenance event timeline for a machine."""
    from modules.ml.services.readiness import get_timeline_for_machine

    result = await db.execute(select(Machines).where(Machines.id == machine_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Machine not found")

    events = await get_timeline_for_machine(machine_id, db, limit=limit)
    return {"success": True, "machine_id": machine_id, "events": events, "count": len(events)}


@router.get("/kpis")
async def get_p7_kpis(db: AsyncSession = Depends(get_db)) -> Dict:
    """
    P7.5: Fleet-wide P7 KPIs derived from existing data.
    - stock_readiness_rate: % machines without active PARTS_SHORTAGE alert
    - adoption_rate: % machines with at least one ML prediction log
    - active_shortages: count of active PARTS_SHORTAGE alerts
    - draft_wos_pending: count of DRAFT work orders linked to P7 alerts
    """
    from models.alertes import Alert, AlertType
    from models.ml_prediction_log import MlPredictionLog
    from models.ordres_travail import Ordres_travail, OrdreStatut
    from sqlalchemy import func, distinct

    # Total machine count
    total_machines_q = await db.execute(select(func.count(Machines.id)))
    total_machines = total_machines_q.scalar() or 1  # avoid div-by-zero

    # Machines with active PARTS_SHORTAGE
    shortage_q = await db.execute(
        select(func.count(distinct(Alert.machine_id))).where(
            and_(Alert.alert_type == AlertType.PARTS_SHORTAGE, Alert.is_active == True)
        )
    )
    shortage_count = shortage_q.scalar() or 0

    # Machines with at least one prediction log
    pred_q = await db.execute(
        select(func.count(distinct(MlPredictionLog.machine_id)))
    )
    predicted_machines = pred_q.scalar() or 0

    # Draft WOs pending approval
    draft_q = await db.execute(
        select(func.count(Ordres_travail.id)).where(
            Ordres_travail.statut == OrdreStatut.DRAFT
        )
    )
    draft_count = draft_q.scalar() or 0

    stock_readiness_rate = round(100.0 * (total_machines - shortage_count) / total_machines, 1)
    adoption_rate        = round(100.0 * predicted_machines / total_machines, 1)

    return {
        "success": True,
        "kpis": {
            "stock_readiness_rate":  stock_readiness_rate,
            "adoption_rate":         adoption_rate,
            "active_shortages":      shortage_count,
            "draft_wos_pending":     draft_count,
            "total_machines":        total_machines,
            "machines_with_predictions": predicted_machines,
        }
    }


@router.get("/procurement/queue")
async def get_procurement_queue(db: AsyncSession = Depends(get_db)) -> Dict:
    """
    P7: List machines with active PARTS_SHORTAGE alerts.
    Used by ADMIN procurement queue widget to review and act on shortfalls.
    Returns: [{machine_id, machine_name, severity, message, created_at}]
    """
    from models.alertes import Alert, AlertType
    from sqlalchemy import and_

    result = await db.execute(
        select(Alert, Machines)
        .join(Machines, Alert.machine_id == Machines.id)
        .where(
            and_(
                Alert.alert_type == AlertType.PARTS_SHORTAGE,
                Alert.is_active == True,
            )
        )
        .order_by(Alert.created_at.desc())
    )
    rows = result.all()

    items = [
        {
            "alert_id":    row.Alert.alert_id,
            "machine_id":  row.Alert.machine_id,
            "machine_name": row.Machines.nom,
            "severity":    row.Alert.severity.value,
            "message":     row.Alert.message,
            "created_at":  row.Alert.created_at.isoformat() if row.Alert.created_at else None,
        }
        for row in rows
    ]
    return {"success": True, "count": len(items), "items": items}


@router.post("/procurement/draft/{machine_id}")
async def create_procurement_draft_endpoint(
    machine_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict:
    """
    P7.4: Create a DRAFT work order from the latest parts_demand shortfall
    for this machine. Deduped — one active draft per machine at a time.
    Human must approve before any reservation commits.
    """
    from modules.ml.services.parts_drafts import create_procurement_draft
    from modules.ml.services.parts_alerts import extract_shortage_items

    # Re-fetch parts_demand from the active PARTS_SHORTAGE alert's context.
    # Simplest approach: call unified-health and extract parts_demand.
    # For now, require caller to pass parts_demand in body or derive from alert.
    # We read the last alert message to confirm shortage exists.
    from models.alertes import Alert, AlertType
    from sqlalchemy import and_

    alert_q = await db.execute(
        select(Alert).where(
            and_(
                Alert.machine_id == machine_id,
                Alert.alert_type == AlertType.PARTS_SHORTAGE,
                Alert.is_active  == True,
            )
        )
    )
    alert = alert_q.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="No active PARTS_SHORTAGE alert for this machine")

    if alert.work_order_id:
        return {"success": False, "message": "Draft already exists", "wo_id": alert.work_order_id}

    # Build minimal parts_demand from alert message (real data comes at T26 persistence)
    # For now create draft with placeholder so the WO is created and linked
    placeholder_demand = {
        "horizon_days": 30,
        "source": "p7_model",
        "items": [{"piece_id": 0, "name": "see alert message", "expected_qty": 1.0,
                   "on_hand": 0, "shortfall": 1.0, "driver": "condition"}],
    }

    wo_id = await create_procurement_draft(
        machine_id=machine_id,
        parts_demand=placeholder_demand,
        created_by=current_user.id if current_user else None,
        db=db,
    )
    if wo_id is None:
        return {"success": False, "message": "Draft already exists or no items to draft"}
    await db.commit()
    return {"success": True, "wo_id": wo_id, "message": "Draft work order created — awaiting approval"}


@router.patch("/procurement/draft/{wo_id}/approve")
async def approve_procurement_draft_endpoint(
    wo_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict:
    """P7.4: Approve draft → SUBMITTED. Enters normal WO workflow."""
    from modules.ml.services.parts_drafts import approve_procurement_draft
    return await approve_procurement_draft(wo_id, current_user.id if current_user else 0, db)


@router.delete("/procurement/draft/{wo_id}")
async def reject_procurement_draft_endpoint(
    wo_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """P7.4: Reject/discard draft → ANNULÉ. Unlinks from PARTS_SHORTAGE alert."""
    from modules.ml.services.parts_drafts import reject_procurement_draft
    return await reject_procurement_draft(wo_id, db)


@router.post("/procurement/quick-action/{machine_id}")
async def quick_action_endpoint(
    machine_id: int,
    dry_run: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict:
    """
    Quick Action — ADMIN one-click: convert ML-recommended parts into real
    pieces + stock. Atomic, concurrency-safe, idempotent. `?dry_run=true`
    previews without writing.
    """
    # ADMIN guard (mirrors rag_docs._require_admin).
    role = (current_user.role.value if hasattr(current_user.role, "value")
            else str(current_user.role or "")).upper()
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


@router.get("/model/metrics")
async def get_ml_model_metrics():
    """
    Get trained model metrics (ROC-AUC, PR-AUC, F1).
    Returns the performance metrics of the P1 failure prediction model.
    """
    metrics = await get_model_metrics()
    if metrics.get("success"):
        return {
            "success": True,
            "model": "p1_failure",
            "metrics": metrics.get("metrics", {})
        }
    return {
        "success": False,
        "error": "Could not retrieve model metrics"
    }


from modules.ml.services.model_registry import scan_models, check_sync
from modules.ml.services.drift import compute_drift, SENSORS
from modules.ml.services.retraining_advisor import recommend_retraining


def _require_admin(current_user: Utilisateurs):
    if not current_user.role or current_user.role.value != "ADMIN":
        raise HTTPException(status_code=403, detail="ADMIN role required.")


async def _drift_rows(db: AsyncSession, start, end):
    cols = [getattr(MlPredictionLog, s) for s in SENSORS]
    stmt = select(*cols).where(
        MlPredictionLog.created_at >= start, MlPredictionLog.created_at < end
    ).limit(2000)
    res = await db.execute(stmt)
    return [dict(zip(SENSORS, row)) for row in res.all()]


@router.get("/model-health")
async def model_health(
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
):
    _require_admin(current_user)
    models = scan_models(_BACKEND_MODELS, _MICRO_MODELS)
    divergences = check_sync(_BACKEND_MODELS, _MICRO_MODELS)
    now = datetime.now(timezone.utc)
    try:
        baseline = await _drift_rows(db, now - timedelta(days=60), now - timedelta(days=30))
        recent = await _drift_rows(db, now - timedelta(days=14), now)
        drift = compute_drift(baseline, recent)
    except Exception:
        drift = {"verdict": "insufficient_data", "sensors": {}}
    try:
        metrics = await get_model_metrics()
    except Exception:
        metrics = {"success": False}
    try:
        stats = await RetrainingService.get_retraining_stats(db)
        ndp = int(stats.get("new_data_points", 0))
    except Exception:
        ndp = 0
    retrain = recommend_retraining(ndp, drift["verdict"])
    return {"models": models, "divergences": divergences,
            "metrics": metrics, "drift": drift, "retrain": retrain}
