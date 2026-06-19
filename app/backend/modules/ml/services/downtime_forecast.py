"""
Downtime forecast — pure functions.
Blends RUL proximity and failure probability into p_failure per horizon.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DOWNTIME_CACHE: Dict[str, Any] = {"data": {}, "timestamp": {}, "ttl": 1800}  # 30 min


def estimate_downtime_hours(
    rul_days: float,
    failure_prob: float,
    horizon_days: int,
    avg_repair_hours: float = 8.0,
) -> Dict[str, Any]:
    """
    Pure function. Returns {horizon_days, p_failure, expected_downtime_hours}.
    failure_prob: 0-100.
    p_failure: 60% weight on failure_prob, 40% on RUL proximity to horizon.
    """
    rul_factor = max(0.0, 1.0 - rul_days / max(float(horizon_days), 1.0))
    prob_factor = min(1.0, failure_prob / 100.0)
    p_failure = min(1.0, prob_factor * 0.6 + rul_factor * 0.4)
    expected = round(p_failure * avg_repair_hours, 2)
    return {
        "horizon_days": horizon_days,
        "p_failure": round(p_failure, 4),
        "expected_downtime_hours": expected,
    }


async def compute_fleet_downtime(db, horizon_days: int) -> Dict[str, Any]:
    """
    Async wrapper. Fetches latest MlPredictionLog per machine, computes avg_repair_hours
    from closed WOs, then calls estimate_downtime_hours for each machine.
    Returns {machines: [...], total_expected_hours, generated_at, horizon_days}.
    """
    from sqlalchemy import select, func
    from models.ml_prediction_log import MlPredictionLog
    from models.machines import Machines
    from models.ordres_travail import Ordres_travail

    now = datetime.utcnow()
    cache_key = str(horizon_days)
    ts = _DOWNTIME_CACHE["timestamp"].get(cache_key)
    if (
        ts is not None
        and _DOWNTIME_CACHE["data"].get(cache_key) is not None
        and (now - ts).total_seconds() < _DOWNTIME_CACHE["ttl"]
    ):
        return _DOWNTIME_CACHE["data"][cache_key]

    # avg_repair_hours from closed WOs
    avg_repair = 8.0
    try:
        wo_result = await db.execute(
            select(Ordres_travail).where(
                Ordres_travail.date_debut.isnot(None),
                Ordres_travail.date_fin.isnot(None),
            ).limit(200)
        )
        wos = wo_result.scalars().all()
        if wos:
            durations = []
            for wo in wos:
                if wo.date_fin and wo.date_debut:
                    h = (wo.date_fin - wo.date_debut).total_seconds() / 3600.0
                    if 0 < h <= 168:  # cap at 1 week
                        durations.append(h)
            if durations:
                avg_repair = sum(durations) / len(durations)
    except Exception:
        pass

    # latest prediction per machine
    latest_subq = (
        select(
            MlPredictionLog.machine_id,
            func.max(MlPredictionLog.id).label("max_id"),
        )
        .group_by(MlPredictionLog.machine_id)
        .subquery()
    )
    logs_res = await db.execute(
        select(MlPredictionLog).join(
            latest_subq,
            (MlPredictionLog.machine_id == latest_subq.c.machine_id)
            & (MlPredictionLog.id == latest_subq.c.max_id),
        )
    )
    logs = {r.machine_id: r for r in logs_res.scalars().all()}

    machines_res = await db.execute(select(Machines.id, Machines.nom))
    machine_names = {r[0]: r[1] for r in machines_res.fetchall()}

    results = []
    for mid, log in logs.items():
        rul = float(log.rul_days or 90)
        prob = float(log.failure_probability or 0)
        est = estimate_downtime_hours(rul, prob, horizon_days, avg_repair)
        results.append({
            "machine_id": mid,
            "machine_name": machine_names.get(mid, f"Machine {mid}"),
            **est,
        })

    results.sort(key=lambda x: x["p_failure"], reverse=True)
    total = round(sum(r["expected_downtime_hours"] for r in results), 2)
    payload = {
        "machines": results,
        "total_expected_hours": total,
        "avg_repair_hours": round(avg_repair, 1),
        "generated_at": now.isoformat(),
        "horizon_days": horizon_days,
    }
    _DOWNTIME_CACHE["data"][cache_key] = payload
    _DOWNTIME_CACHE["timestamp"][cache_key] = now
    return payload
