"""
Schedule optimizer.
Primary: OR-Tools CP-SAT (minimize priority-weighted completion day).
Fallback: greedy round-robin when ortools unavailable.
"""

from __future__ import annotations
import asyncio
import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_SCHEDULE_CACHE: Dict[str, Any] = {"data": None, "timestamp": None, "ttl": 1800}

try:
    from ortools.sat.python import cp_model as _cp_model

    _ORTOOLS_AVAILABLE = True
except ImportError:
    _ORTOOLS_AVAILABLE = False
    logger.warning(
        "ortools not installed — schedule optimizer will use greedy fallback"
    )


def _greedy_schedule(
    work_orders: List[Dict[str, Any]],
    technician_ids: List[int],
    _horizon_days: int,
) -> Dict[str, Any]:
    if not work_orders or not technician_ids:
        return {"assignments": [], "makespan_days": 0, "solved": True, "fallback": True}

    sorted_wos = sorted(work_orders, key=lambda w: w.get("priority", 1), reverse=True)
    tech_next_day = dict.fromkeys(technician_ids, 0)
    assignments = []

    for i, wo in enumerate(sorted_wos):
        tech_id = technician_ids[i % len(technician_ids)]
        est_hours = float(wo.get("estimated_hours", 4.0))
        duration_days = max(1, math.ceil(est_hours / 8.0))

        start_day = tech_next_day[tech_id]
        if not wo.get("parts_ready", True):
            start_day = max(start_day, 3)

        end_day = start_day + duration_days
        tech_next_day[tech_id] = end_day

        assignments.append(
            {
                "wo_id": wo["id"],
                "technician_id": tech_id,
                "start_day": start_day,
                "end_day": end_day,
            }
        )

    makespan = max((a["end_day"] for a in assignments), default=0)
    return {
        "assignments": assignments,
        "makespan_days": makespan,
        "solved": True,
        "fallback": True,
    }


def _ortools_schedule(
    work_orders: List[Dict[str, Any]],
    technician_ids: List[int],
    horizon_days: int,
    max_solve_seconds: int = 5,
) -> Dict[str, Any]:
    model = _cp_model.CpModel()
    n_techs = len(technician_ids)
    max_h = horizon_days
    starts, durations, ends, techs = [], [], [], []

    for wo in work_orders:
        est_h = float(wo.get("estimated_hours", 4.0))
        dur = max(1, math.ceil(est_h / 8.0))
        min_start = 3 if not wo.get("parts_ready", True) else 0

        s = model.NewIntVar(min_start, max_h, f"start_{wo['id']}")
        e = model.NewIntVar(min_start + dur, max_h + dur, f"end_{wo['id']}")
        model.Add(e == s + dur)
        t = model.NewIntVar(0, n_techs - 1, f"tech_{wo['id']}")
        starts.append(s)
        ends.append(e)
        durations.append(dur)
        techs.append(t)

    for tech_idx in range(n_techs):
        intervals = []
        for i, wo in enumerate(work_orders):
            dur = durations[i]
            is_assigned = model.NewBoolVar(f"assigned_{wo['id']}_t{tech_idx}")
            model.Add(techs[i] == tech_idx).OnlyEnforceIf(is_assigned)
            model.Add(techs[i] != tech_idx).OnlyEnforceIf(is_assigned.Not())
            opt_iv = model.NewOptionalIntervalVar(
                starts[i], dur, ends[i], is_assigned, f"interval_{wo['id']}_t{tech_idx}"
            )
            intervals.append(opt_iv)
        model.AddNoOverlap(intervals)

    obj_terms = []
    for i, wo in enumerate(work_orders):
        priority = int(wo.get("priority", 1))
        obj_terms.append(priority * ends[i])
    model.Minimize(sum(obj_terms))

    solver = _cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_solve_seconds
    status = solver.Solve(model)

    if status in (_cp_model.OPTIMAL, _cp_model.FEASIBLE):
        assignments = []
        for i, wo in enumerate(work_orders):
            tech_idx = solver.Value(techs[i])
            assignments.append(
                {
                    "wo_id": wo["id"],
                    "technician_id": technician_ids[tech_idx],
                    "start_day": solver.Value(starts[i]),
                    "end_day": solver.Value(ends[i]),
                }
            )
        makespan = max((a["end_day"] for a in assignments), default=0)
        return {
            "assignments": assignments,
            "makespan_days": makespan,
            "solved": True,
            "fallback": False,
        }

    logger.warning("OR-Tools status %s — falling back to greedy", status)
    result = _greedy_schedule(work_orders, technician_ids, horizon_days)
    result["fallback"] = True
    return result


def optimize_schedule(
    work_orders: List[Dict[str, Any]],
    technician_ids: List[int],
    horizon_days: int = 30,
    max_solve_seconds: int = 5,
) -> Dict[str, Any]:
    if not _ORTOOLS_AVAILABLE:
        return _greedy_schedule(work_orders, technician_ids, horizon_days)
    return _ortools_schedule(
        work_orders, technician_ids, horizon_days, max_solve_seconds
    )


def _wo_to_dict(wo) -> Dict[str, Any]:
    """Convert OrdresTravail ORM object to scheduler-compatible dict."""
    est = 4.0
    if wo.date_debut and wo.date_fin:
        h = (wo.date_fin - wo.date_debut).total_seconds() / 3600.0
        if 0 < h <= 168:
            est = h
    priority = 3
    if hasattr(wo, "priority") and wo.priority:
        try:
            priority = int(wo.priority)
        except (ValueError, TypeError):
            pass
    return {"id": wo.id, "priority": priority, "estimated_hours": est, "parts_ready": True, "titre": wo.titre or f"WO #{wo.id}"}


async def compute_schedule(db, horizon_days: int) -> Dict[str, Any]:
    from sqlalchemy import select
    from models.ordres_travail import OrdresTravail, OrdreStatut
    from models.utilisateurs import Utilisateurs

    now = datetime.now(timezone.utc)
    if (
        _SCHEDULE_CACHE["data"] is not None
        and _SCHEDULE_CACHE["timestamp"] is not None
        and (now - _SCHEDULE_CACHE["timestamp"]).total_seconds() < _SCHEDULE_CACHE["ttl"]
    ):
        return _SCHEDULE_CACHE["data"]

    wo_res = await db.execute(
        select(OrdresTravail)
        .where(OrdresTravail.statut.in_([OrdreStatut.ASSIGNED, OrdreStatut.IN_PROGRESS]))
        .limit(100)
    )
    work_orders = [_wo_to_dict(wo) for wo in wo_res.scalars().all()]

    tech_res = await db.execute(select(Utilisateurs).where(Utilisateurs.role == "TECHNICIEN"))
    tech_ids = [u.id for u in tech_res.scalars().all()] or [0]

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, optimize_schedule, work_orders, tech_ids, horizon_days)

    wo_titles = {wo["id"]: wo["titre"] for wo in work_orders}
    for a in result.get("assignments", []):
        a["titre"] = wo_titles.get(a["wo_id"], f"WO #{a['wo_id']}")

    _SCHEDULE_CACHE["data"] = result
    _SCHEDULE_CACHE["timestamp"] = now
    return result


def invalidate_schedule_cache() -> None:
    _SCHEDULE_CACHE["data"] = None
    _SCHEDULE_CACHE["timestamp"] = None
