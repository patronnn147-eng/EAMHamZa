"""Fleet-wide dashboard and critical-risk endpoints."""
import asyncio
from datetime import datetime, timezone
from typing import Annotated, Dict, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.ml_client import is_ml_service_available, ml_client
from models.machines import Machines
from models.machine_telemetry import MachineTelemetry
from models.ml_prediction_log import MlPredictionLog
from models.ordres_intervention import OrdresIntervention
from services.inventory.pieces import batch_get_parts_readiness

from ..rul_calculator import RULCalculator
from ._common import _entries_to_log_dicts, _latest_sensors

router = APIRouter(tags=["Machine Learning"])

# Simple in-memory cache for fleet dashboard
_fleet_cache = {
    "data": None,
    "timestamp": None,
    "ttl_seconds": 300,  # 5 minutes cache
}


@router.get("/fleet/critical")
async def get_fleet_critical_predictions(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Get machines with the highest risk of failure across the fleet.
    Returns only HIGH and CRITICAL risk machines, sorted by rul_days ascending.
    """
    result = await db.execute(select(Machines))
    machines = result.scalars().all()
    predictions = []

    # Single query for all interventions — avoids N per-machine round-trips.
    all_oi_result = await db.execute(select(OrdresIntervention))
    _oi_by_machine: dict = {}
    for _oi in all_oi_result.scalars().all():
        _oi_by_machine.setdefault(_oi.machine_id, []).append(_oi)

    for machine in machines:
        interventions = _oi_by_machine.get(machine.id, [])
        pred = RULCalculator.calculate_rul(machine, list(interventions))
        if pred["risk_level"] in ["CRITICAL", "HIGH"]:
            predictions.append(pred)

    return {"machines": sorted(predictions, key=lambda x: x["rul_days"])}


def _fusion_from_log(log) -> Optional[Dict]:
    """Build a synthetic fusion_result dict from a cached MlPredictionLog row.

    Degraded-mode fallback only — used when live telemetry is unavailable or
    the ML microservice is down. It has no `unified_health_score` key, so
    RULCalculator._compute_health_score() falls back to the `fallback_additive`
    formula rather than reporting a real DST-fused score.
    """
    if log is None:
        return None
    return {
        "p1_failure_probability": float(log.failure_probability or 0.0),
        "p3_rul_days": float(log.rul_days) if log.rul_days is not None else None,
        "p4_is_anomaly": bool(log.is_anomaly or False),
        "p4_anomaly_score": float(log.anomaly_score or 0.0),
        "p5_predicted_priority": log.predicted_priority,
        "p2_failure_types": {},
    }


async def _fetch_interventions(machine_id: int, db: AsyncSession):
    """Fetch interventions for a single machine directly from DB."""
    result = await db.execute(
        select(OrdresIntervention).where(OrdresIntervention.machine_id == machine_id)
    )
    return result.scalars().all()


async def _fleet_telemetry_by_machine(db: AsyncSession) -> Dict[int, list]:
    """Batch-fetch telemetry for every machine in one query, grouped and capped
    to the same 500-entry oldest-first window `_get_telemetry_history` uses.

    Must be prefetched up front, not queried inside `_process_single_machine`:
    that function runs under `asyncio.gather`, and AsyncSession isn't safe for
    concurrent use across tasks sharing the same session.
    """
    filters = []
    if not settings.ml_allow_synthetic_telemetry:
        filters.append(MachineTelemetry.is_synthetic.is_(False))

    result = await db.execute(
        select(MachineTelemetry).where(*filters).order_by(MachineTelemetry.recorded_at.asc())
    )
    by_machine: Dict[int, list] = {}
    for entry in result.scalars().all():
        by_machine.setdefault(entry.machine_id, []).append(entry)
    for machine_id, entries in by_machine.items():
        if len(entries) > 500:
            by_machine[machine_id] = entries[-500:]
    return by_machine


async def _process_single_machine(
    machine: Machines,
    db: AsyncSession,
    interventions_by_machine: dict = None,
    latest_logs_by_machine: dict = None,
    telemetry_by_machine: dict = None,
    parts_readiness_map: dict = None,
    ml_available: bool = False,
) -> Dict:
    """Helper to process single machine prediction.

    Runs the same live DST fusion call as GET /machines/{id}/unified-health
    (telemetry history -> ml_client.predict_all) so the fleet card's health
    score matches the detail page's — not a cached-log reconstruction. Falls
    back to the cheap `_fusion_from_log` reconstruction (fallback_additive
    formula) only when telemetry is missing or the ML microservice is down.

    Args:
        interventions_by_machine: pre-fetched dict {machine_id: [OrdresIntervention]}
        latest_logs_by_machine: pre-fetched dict {machine_id: MlPredictionLog} — latest log row per machine, degraded-mode fallback only
        telemetry_by_machine: pre-fetched dict {machine_id: [MachineTelemetry]} — see _fleet_telemetry_by_machine
        parts_readiness_map: pre-fetched dict {machine_id: status} -- inventory readiness per machine
        ml_available: checked once per dashboard refresh, not per machine — is_ml_service_available()
            makes an uncached HTTP call, so re-checking it N times per machine would be N redundant pings
    """
    if interventions_by_machine is not None:
        interventions = interventions_by_machine.get(machine.id, [])
    else:
        interventions = await _fetch_interventions(machine.id, db)

    telemetry_entries = (telemetry_by_machine or {}).get(machine.id, [])
    _air, _proc, _rpm, _torq, _wear = _latest_sensors(telemetry_entries)

    fusion_result: Optional[Dict] = None
    try:
        if telemetry_entries and ml_available:
            fusion_result = await ml_client.predict_all(
                air_temperature=_air,
                process_temperature=_proc,
                rotational_speed=_rpm,
                torque=_torq,
                tool_wear=int(_wear),
                machine_id=machine.id,
                telemetry_logs=_entries_to_log_dicts(machine.id, telemetry_entries),
            )
    except Exception:
        fusion_result = None

    if fusion_result is None:
        # Degraded mode: no live telemetry or ML service unavailable.
        log = (latest_logs_by_machine or {}).get(machine.id) if latest_logs_by_machine is not None else None
        fusion_result = _fusion_from_log(log)

    pred = RULCalculator.calculate_rul(
        machine,
        list(interventions),
        telemetry_entries=telemetry_entries or None,
        fusion_result=fusion_result,
    )
    pred["zone"] = machine.zone
    pred["sous_zone"] = machine.sous_zone
    pred["statut"] = machine.statut
    pred["parts_ready"] = (parts_readiness_map or {}).get(machine.id, "OK")
    return pred


@router.get("/fleet/dashboard")
async def get_fleet_dashboard(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    PDCA Fleet Dashboard: Full overview of ALL machines with ML predictions.
    Cached for 5 minutes + parallel processing for speed.
    """
    now = datetime.now(timezone.utc)

    # Check cache
    if (
        _fleet_cache["data"] is not None
        and _fleet_cache["timestamp"] is not None
        and (now - _fleet_cache["timestamp"]).total_seconds()
        < _fleet_cache["ttl_seconds"]
    ):
        return _fleet_cache["data"]

    # Build dashboard fresh - parallel processing
    result = await db.execute(select(Machines))
    machines = result.scalars().all()

    # Fetch ALL interventions in a single query and group by machine_id.
    # Avoids N per-machine queries (was O(N) DB round-trips, now O(1)).
    all_interventions_result = await db.execute(select(OrdresIntervention))
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

    # Batch-fetch telemetry for the whole fleet (one query, see docstring on
    # _fleet_telemetry_by_machine for why this can't happen per-task below).
    _telemetry_by_machine = await _fleet_telemetry_by_machine(db)

    # Batch-fetch inventory parts readiness for all machines (single query).
    try:
        _parts_readiness_map = await batch_get_parts_readiness(db)
    except Exception:
        _parts_readiness_map = {}

    # Checked once for the whole dashboard refresh, not per machine (uncached HTTP call).
    try:
        _ml_available = await is_ml_service_available()
    except Exception:
        _ml_available = False

    # Process all machines in parallel — DB reads are all prefetched above;
    # only the per-machine ml_client HTTP calls run concurrently here.
    tasks = [
        _process_single_machine(
            m,
            db,
            _interventions_by_machine,
            _latest_logs_by_machine,
            _telemetry_by_machine,
            _parts_readiness_map,
            _ml_available,
        )
        for m in machines
    ]
    dashboard = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out errors
    dashboard = [d for d in dashboard if isinstance(d, dict)]

    # Sort: CRITICAL first, then HIGH, then MEDIUM, then LOW
    risk_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    sorted_dashboard = sorted(
        dashboard, key=lambda x: (risk_order.get(x["risk_level"], 4), x["rul_days"])
    )

    # Cache result
    _fleet_cache["data"] = sorted_dashboard
    _fleet_cache["timestamp"] = now

    return sorted_dashboard


@router.post("/fleet/dashboard/refresh")
async def refresh_fleet_dashboard():
    """Force refresh the fleet dashboard cache."""
    _fleet_cache["data"] = None
    _fleet_cache["timestamp"] = None
    return {
        "status": "cache_cleared",
        "message": "Dashboard cache cleared. Next request will rebuild.",
    }
