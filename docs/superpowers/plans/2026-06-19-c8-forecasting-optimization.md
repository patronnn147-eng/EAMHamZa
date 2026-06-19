# C8 Forecasting & Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add short-horizon (7/30/60-day) downtime, labor, and budget forecasts plus an OR-Tools schedule optimizer, surfaced as dashboard embeds and a dedicated `/forecast` page.

**Architecture:** Four pure backend service files (deterministic, fully testable) wired into the existing ML router via 6 new endpoints. OR-Tools CP-SAT runs in `asyncio.run_in_executor` (non-blocking) with a greedy round-robin fallback when the library is unavailable. Frontend: two embed components (dashboard tile + machine tab) plus a dedicated `/forecast` page with role-aware layout.

**Tech Stack:** Python/FastAPI backend, `ortools>=9.7` (new dep), React 19 + TypeScript, `recharts` (already installed), raw `fetch` + Bearer token pattern.

---

## File Map

**Create (backend):**
- `app/backend/modules/ml/services/downtime_forecast.py`
- `app/backend/modules/ml/services/labor_forecast.py`
- `app/backend/modules/ml/services/budget_forecast.py`
- `app/backend/modules/ml/services/schedule_optimizer.py`
- `tests/backend/forecast_downtime.test.py`
- `tests/backend/forecast_labor.test.py`
- `tests/backend/forecast_budget.test.py`
- `tests/backend/forecast_schedule.test.py`

**Create (frontend):**
- `app/frontend/src/modules/shared/dashboard/ForecastSummaryTile.tsx`
- `app/frontend/src/modules/shared/machines/components/MachineForecastPanel.tsx`
- `app/frontend/src/modules/cheftech/forecast/ForecastDashboard.tsx`
- `app/frontend/src/modules/cheftech/forecast/DowntimeForecastChart.tsx`
- `app/frontend/src/modules/cheftech/forecast/LaborForecastChart.tsx`
- `app/frontend/src/modules/cheftech/forecast/BudgetForecastCard.tsx`
- `app/frontend/src/modules/cheftech/forecast/ScheduleOptimizerPanel.tsx`
- `app/frontend/src/modules/cheftech/forecast/TechnicianScheduleView.tsx`
- `app/frontend/src/modules/cheftech/forecast/forecastTransforms.test.ts`

**Modify:**
- `app/backend/requirements.txt` — add `ortools>=9.7`
- `app/backend/modules/ml/router.py` — add 6 endpoints + `_require_planner` + `_FORECAST_CACHE`
- `app/frontend/src/app/routing/AppRoutes.tsx` — add `/forecast` route
- `app/frontend/src/modules/cheftech/CheftechDashboard.tsx` — embed `ForecastSummaryTile`
- `app/frontend/src/modules/shared/MachineDetailPage.tsx` — add 5th "Prévisions" tab

---

## Task 1: Downtime Forecast Service

**Files:**
- Create: `app/backend/modules/ml/services/downtime_forecast.py`
- Test: `tests/backend/forecast_downtime.test.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/backend/forecast_downtime.test.py
from modules.ml.services.downtime_forecast import estimate_downtime_hours


def test_high_risk_machine():
    result = estimate_downtime_hours(rul_days=5, failure_prob=85, horizon_days=30)
    assert result["p_failure"] > 0.7
    assert result["expected_downtime_hours"] > 0
    assert result["horizon_days"] == 30


def test_healthy_machine():
    result = estimate_downtime_hours(rul_days=200, failure_prob=5, horizon_days=30)
    assert result["p_failure"] < 0.2


def test_p_failure_clamps_to_one():
    result = estimate_downtime_hours(rul_days=0, failure_prob=100, horizon_days=7)
    assert result["p_failure"] <= 1.0


def test_short_horizon_lower_than_long():
    r7 = estimate_downtime_hours(rul_days=20, failure_prob=50, horizon_days=7)
    r60 = estimate_downtime_hours(rul_days=20, failure_prob=50, horizon_days=60)
    assert r7["p_failure"] <= r60["p_failure"]


def test_custom_repair_hours():
    result = estimate_downtime_hours(rul_days=5, failure_prob=80, horizon_days=30, avg_repair_hours=12.0)
    assert result["expected_downtime_hours"] == round(result["p_failure"] * 12.0, 2)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd C:/Users/Admin/Downloads/EAM/EAMSagemCom
python -m pytest tests/backend/forecast_downtime.test.py -v
```
Expected: `ModuleNotFoundError: No module named 'modules.ml.services.downtime_forecast'`

- [ ] **Step 3: Implement downtime_forecast.py**

```python
# app/backend/modules/ml/services/downtime_forecast.py
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/backend/forecast_downtime.test.py -v
```
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add app/backend/modules/ml/services/downtime_forecast.py tests/backend/forecast_downtime.test.py
git commit -m "feat(c8): downtime forecast pure service + tests"
```

---

## Task 2: Labor Forecast Service

**Files:**
- Create: `app/backend/modules/ml/services/labor_forecast.py`
- Test: `tests/backend/forecast_labor.test.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/backend/forecast_labor.test.py
from modules.ml.services.labor_forecast import forecast_labor


def test_basic_demand():
    machine_forecasts = [
        {"expected_downtime_hours": 10.0},
        {"expected_downtime_hours": 6.0},
    ]
    result = forecast_labor(
        machine_forecasts=machine_forecasts,
        open_wo_count=5,
        avg_wo_hours=4.0,
        technician_count=3,
        horizon_days=30,
    )
    # demand = 16 (machines) + 20 (open WOs) = 36
    assert result["demand_hours"] == 36.0
    assert result["capacity_hours"] > 0
    assert 0 <= result["coverage_pct"] <= 100


def test_overload_flag():
    machine_forecasts = [{"expected_downtime_hours": 500.0}]
    result = forecast_labor(
        machine_forecasts=machine_forecasts,
        open_wo_count=0,
        avg_wo_hours=4.0,
        technician_count=1,
        horizon_days=7,
    )
    assert result["overload"] is True


def test_no_overload_when_plenty_capacity():
    machine_forecasts = [{"expected_downtime_hours": 2.0}]
    result = forecast_labor(
        machine_forecasts=machine_forecasts,
        open_wo_count=1,
        avg_wo_hours=4.0,
        technician_count=10,
        horizon_days=30,
    )
    assert result["overload"] is False


def test_zero_technicians_graceful():
    result = forecast_labor(
        machine_forecasts=[{"expected_downtime_hours": 8.0}],
        open_wo_count=2,
        avg_wo_hours=4.0,
        technician_count=0,
        horizon_days=30,
    )
    assert result["coverage_pct"] == 0.0
    assert result["overload"] is True


def test_breakdown_sums_to_demand():
    machine_forecasts = [{"expected_downtime_hours": 5.0}]
    result = forecast_labor(
        machine_forecasts=machine_forecasts,
        open_wo_count=3,
        avg_wo_hours=2.0,
        technician_count=2,
        horizon_days=30,
    )
    b = result["breakdown"]
    assert abs((b["predicted_failure_hours"] + b["open_wo_backlog_hours"]) - result["demand_hours"]) < 0.01
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/backend/forecast_labor.test.py -v
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement labor_forecast.py**

```python
# app/backend/modules/ml/services/labor_forecast.py
"""Labor demand/capacity forecast — pure function."""
from __future__ import annotations
from typing import Any, Dict, List


def forecast_labor(
    machine_forecasts: List[Dict[str, Any]],
    open_wo_count: int,
    avg_wo_hours: float,
    technician_count: int,
    horizon_days: int,
) -> Dict[str, Any]:
    """
    Pure function.
    demand  = sum(expected_downtime_hours) + open_wo_count * avg_wo_hours
    capacity = technician_count * 8h * workdays (horizon * 5/7)
    Returns {demand_hours, capacity_hours, coverage_pct, overload, breakdown}.
    """
    predicted_hours = sum(float(m.get("expected_downtime_hours", 0)) for m in machine_forecasts)
    backlog_hours = float(open_wo_count) * float(avg_wo_hours)
    demand = round(predicted_hours + backlog_hours, 1)

    workdays = max(1, round(horizon_days * 5 / 7))
    capacity = float(technician_count * 8 * workdays)

    if technician_count == 0 or capacity == 0:
        coverage = 0.0
    else:
        coverage = round(min(100.0, capacity / max(demand, 0.01) * 100.0), 1)

    return {
        "demand_hours": demand,
        "capacity_hours": capacity,
        "coverage_pct": coverage,
        "overload": demand > capacity,
        "technician_count": technician_count,
        "workdays": workdays,
        "breakdown": {
            "predicted_failure_hours": round(predicted_hours, 1),
            "open_wo_backlog_hours": round(backlog_hours, 1),
        },
    }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/backend/forecast_labor.test.py -v
```
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add app/backend/modules/ml/services/labor_forecast.py tests/backend/forecast_labor.test.py
git commit -m "feat(c8): labor forecast pure service + tests"
```

---

## Task 3: Budget Forecast Service

**Files:**
- Create: `app/backend/modules/ml/services/budget_forecast.py`
- Test: `tests/backend/forecast_budget.test.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/backend/forecast_budget.test.py
import os
from modules.ml.services.budget_forecast import forecast_budget, LABOR_RATE_DEFAULT


def test_labor_only():
    result = forecast_budget(labor_demand_hours=10.0, parts_reorder_items=[])
    assert result["labor_cost"] == round(10.0 * LABOR_RATE_DEFAULT, 2)
    assert result["parts_cost"] == 0.0
    assert result["total"] == result["labor_cost"]
    assert result["currency"] == "EUR"


def test_parts_cost_aggregated():
    items = [
        {"reorder_qty_suggested": 3, "unit_price": 20.0},
        {"reorder_qty_suggested": 1, "unit_price": 150.0},
    ]
    result = forecast_budget(labor_demand_hours=0.0, parts_reorder_items=items)
    assert result["parts_cost"] == 3 * 20.0 + 1 * 150.0


def test_missing_unit_price_defaults_zero():
    items = [{"reorder_qty_suggested": 5}]  # no unit_price key
    result = forecast_budget(labor_demand_hours=0.0, parts_reorder_items=items)
    assert result["parts_cost"] == 0.0


def test_total_equals_labor_plus_parts():
    items = [{"reorder_qty_suggested": 2, "unit_price": 50.0}]
    result = forecast_budget(labor_demand_hours=8.0, parts_reorder_items=items)
    assert abs(result["total"] - (result["labor_cost"] + result["parts_cost"])) < 0.01


def test_custom_labor_rate():
    result = forecast_budget(labor_demand_hours=4.0, parts_reorder_items=[], labor_rate=100.0)
    assert result["labor_cost"] == 400.0


def test_breakdown_has_two_entries():
    result = forecast_budget(labor_demand_hours=5.0, parts_reorder_items=[])
    assert len(result["breakdown"]) == 2
    labels = {e["label"] for e in result["breakdown"]}
    assert "Main-d'œuvre" in labels
    assert "Pièces de rechange" in labels
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/backend/forecast_budget.test.py -v
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement budget_forecast.py**

```python
# app/backend/modules/ml/services/budget_forecast.py
"""Budget forecast — pure function. Labor + parts reorder cost."""
from __future__ import annotations
import os
from typing import Any, Dict, List

LABOR_RATE_DEFAULT: float = float(os.getenv("LABOR_RATE_EUR", "50.0"))


def forecast_budget(
    labor_demand_hours: float,
    parts_reorder_items: List[Dict[str, Any]],
    labor_rate: float = LABOR_RATE_DEFAULT,
) -> Dict[str, Any]:
    """
    Pure function.
    labor_cost = labor_demand_hours * labor_rate
    parts_cost = sum(reorder_qty_suggested * unit_price) — unit_price defaults 0 if absent
    Returns {labor_cost, parts_cost, total, currency, breakdown[]}.
    """
    labor_cost = round(labor_demand_hours * labor_rate, 2)
    parts_cost = round(
        sum(
            float(i.get("reorder_qty_suggested", 0)) * float(i.get("unit_price", 0.0))
            for i in parts_reorder_items
        ),
        2,
    )
    total = round(labor_cost + parts_cost, 2)
    return {
        "labor_cost": labor_cost,
        "parts_cost": parts_cost,
        "total": total,
        "currency": "EUR",
        "breakdown": [
            {"label": "Main-d'œuvre", "value": labor_cost},
            {"label": "Pièces de rechange", "value": parts_cost},
        ],
    }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/backend/forecast_budget.test.py -v
```
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add app/backend/modules/ml/services/budget_forecast.py tests/backend/forecast_budget.test.py
git commit -m "feat(c8): budget forecast pure service + tests"
```

---

## Task 4: Schedule Optimizer Service

**Files:**
- Create: `app/backend/modules/ml/services/schedule_optimizer.py`
- Test: `tests/backend/forecast_schedule.test.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/backend/forecast_schedule.test.py
import pytest
from modules.ml.services.schedule_optimizer import optimize_schedule, _greedy_schedule


WOS = [
    {"id": 1, "priority": 5, "estimated_hours": 8.0, "parts_ready": True},
    {"id": 2, "priority": 3, "estimated_hours": 4.0, "parts_ready": True},
    {"id": 3, "priority": 1, "estimated_hours": 2.0, "parts_ready": False},
]
TECH_IDS = [101, 102]


# --- Greedy fallback tests (always run, no ortools dep) ---

def test_greedy_assigns_all_wos():
    result = _greedy_schedule(WOS, TECH_IDS, horizon_days=30)
    assert len(result["assignments"]) == len(WOS)


def test_greedy_each_wo_has_required_fields():
    result = _greedy_schedule(WOS, TECH_IDS, horizon_days=30)
    for a in result["assignments"]:
        assert "wo_id" in a
        assert "technician_id" in a
        assert "start_day" in a
        assert "end_day" in a
        assert a["end_day"] >= a["start_day"]


def test_greedy_parts_not_ready_deferred():
    result = _greedy_schedule(WOS, TECH_IDS, horizon_days=30)
    deferred = next(a for a in result["assignments"] if a["wo_id"] == 3)
    assert deferred["start_day"] >= 3  # parts_ready=False → min 3-day defer


def test_greedy_fallback_flag():
    result = _greedy_schedule(WOS, TECH_IDS, horizon_days=30)
    assert result["fallback"] is True
    assert result["solved"] is True


def test_greedy_empty_wos():
    result = _greedy_schedule([], TECH_IDS, horizon_days=30)
    assert result["assignments"] == []


def test_greedy_empty_technicians():
    result = _greedy_schedule(WOS, [], horizon_days=30)
    assert result["assignments"] == []


# --- OR-Tools path (skip if not installed) ---

ortools = pytest.importorskip("ortools", reason="ortools not installed — skipping CP-SAT path")


def test_ortools_path_returns_valid_structure():
    result = optimize_schedule(WOS, TECH_IDS, horizon_days=30)
    assert "assignments" in result
    assert "solved" in result
    assert "fallback" in result
    assert isinstance(result["assignments"], list)


def test_ortools_high_priority_scheduled_earlier():
    result = optimize_schedule(WOS, TECH_IDS, horizon_days=30)
    if result["solved"] and not result["fallback"]:
        p5 = next((a for a in result["assignments"] if a["wo_id"] == 1), None)
        p1 = next((a for a in result["assignments"] if a["wo_id"] == 3), None)
        if p5 and p1:
            assert p5["start_day"] <= p1["start_day"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/backend/forecast_schedule.test.py -v
```
Expected: `ModuleNotFoundError: No module named 'modules.ml.services.schedule_optimizer'`

- [ ] **Step 3: Implement schedule_optimizer.py**

```python
# app/backend/modules/ml/services/schedule_optimizer.py
"""
Schedule optimizer.
Primary: OR-Tools CP-SAT (minimize priority-weighted completion day).
Fallback: greedy round-robin when ortools unavailable.
"""
from __future__ import annotations
import asyncio
import logging
import math
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_SCHEDULE_CACHE: Dict[str, Any] = {"data": None, "timestamp": None, "ttl": 1800}

try:
    from ortools.sat.python import cp_model as _cp_model
    _ORTOOLS_AVAILABLE = True
except ImportError:
    _ORTOOLS_AVAILABLE = False
    logger.warning("ortools not installed — schedule optimizer will use greedy fallback")


def _greedy_schedule(
    work_orders: List[Dict[str, Any]],
    technician_ids: List[int],
    horizon_days: int,
) -> Dict[str, Any]:
    """Round-robin greedy assignment. Always available (no ortools dep)."""
    if not work_orders or not technician_ids:
        return {"assignments": [], "makespan_days": 0, "solved": True, "fallback": True}

    # Sort by priority desc
    sorted_wos = sorted(work_orders, key=lambda w: w.get("priority", 1), reverse=True)

    # Track next available day per technician
    tech_next_day = {t: 0 for t in technician_ids}
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

        assignments.append({
            "wo_id": wo["id"],
            "technician_id": tech_id,
            "start_day": start_day,
            "end_day": end_day,
        })

    makespan = max((a["end_day"] for a in assignments), default=0)
    return {"assignments": assignments, "makespan_days": makespan, "solved": True, "fallback": True}


def _ortools_schedule(
    work_orders: List[Dict[str, Any]],
    technician_ids: List[int],
    horizon_days: int,
    max_solve_seconds: int = 5,
) -> Dict[str, Any]:
    """CP-SAT optimizer. Only called when ortools is available."""
    model = _cp_model.CpModel()
    n_wos = len(work_orders)
    n_techs = len(technician_ids)

    # For each WO: start day, duration (in days), interval, assigned tech
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
        starts.append(s); ends.append(e); durations.append(dur); techs.append(t)

    # Each technician works at most 1 WO per day-slot (simplified bin constraint)
    # Use no-overlap per technician via optional intervals
    for tech_idx in range(n_techs):
        intervals = []
        for i, wo in enumerate(work_orders):
            dur = durations[i]
            is_assigned = model.NewBoolVar(f"assigned_{wo['id']}_t{tech_idx}")
            model.Add(techs[i] == tech_idx).OnlyEnforceIf(is_assigned)
            model.Add(techs[i] != tech_idx).OnlyEnforceIf(is_assigned.Not())
            opt_iv = model.NewOptionalIntervalVar(
                starts[i], dur, ends[i], is_assigned,
                f"interval_{wo['id']}_t{tech_idx}"
            )
            intervals.append(opt_iv)
        model.AddNoOverlap(intervals)

    # Objective: minimize sum(priority * end_day)
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
            assignments.append({
                "wo_id": wo["id"],
                "technician_id": technician_ids[tech_idx],
                "start_day": solver.Value(starts[i]),
                "end_day": solver.Value(ends[i]),
            })
        makespan = max((a["end_day"] for a in assignments), default=0)
        return {"assignments": assignments, "makespan_days": makespan, "solved": True, "fallback": False}

    # Timeout or infeasible — fall back to greedy
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
    """Entry point. Uses OR-Tools if available, else greedy."""
    if not _ORTOOLS_AVAILABLE:
        return _greedy_schedule(work_orders, technician_ids, horizon_days)
    return _ortools_schedule(work_orders, technician_ids, horizon_days, max_solve_seconds)


async def compute_schedule(db, horizon_days: int) -> Dict[str, Any]:
    """
    Async wrapper for the router.
    Fetches open WOs + TECHNICIEN user IDs, runs optimizer in thread pool.
    Results cached 30 min.
    """
    from sqlalchemy import select
    from models.ordres_travail import Ordres_travail, OrdreStatut
    from models.utilisateurs import Utilisateurs

    now = datetime.utcnow()
    if (
        _SCHEDULE_CACHE["data"] is not None
        and _SCHEDULE_CACHE["timestamp"] is not None
        and (now - _SCHEDULE_CACHE["timestamp"]).total_seconds() < _SCHEDULE_CACHE["ttl"]
    ):
        return _SCHEDULE_CACHE["data"]

    # Fetch open WOs
    wo_res = await db.execute(
        select(Ordres_travail).where(
            Ordres_travail.statut.in_([OrdreStatut.PLANIFIE, OrdreStatut.EN_COURS])
        ).limit(100)
    )
    wos_db = wo_res.scalars().all()

    work_orders = []
    for wo in wos_db:
        # estimated hours: from WO history if available, else 4h
        est = 4.0
        if wo.date_debut and wo.date_fin:
            h = (wo.date_fin - wo.date_debut).total_seconds() / 3600.0
            if 0 < h <= 168:
                est = h
        priority = 3  # default medium
        if hasattr(wo, 'priority') and wo.priority:
            try:
                priority = int(wo.priority)
            except (ValueError, TypeError):
                pass
        work_orders.append({
            "id": wo.id,
            "priority": priority,
            "estimated_hours": est,
            "parts_ready": True,  # parts_ready check from stock not done here — conservative True
            "titre": wo.titre or f"WO #{wo.id}",
        })

    # Fetch TECHNICIEN user IDs
    tech_res = await db.execute(
        select(Utilisateurs).where(Utilisateurs.role == "TECHNICIEN")
    )
    tech_ids = [u.id for u in tech_res.scalars().all()]

    if not tech_ids:
        tech_ids = [0]  # dummy so optimizer doesn't crash on empty fleet

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, optimize_schedule, work_orders, tech_ids, horizon_days
    )

    # Enrich assignments with WO titles for frontend
    wo_titles = {wo["id"]: wo["titre"] for wo in work_orders}
    for a in result.get("assignments", []):
        a["titre"] = wo_titles.get(a["wo_id"], f"WO #{a['wo_id']}")

    _SCHEDULE_CACHE["data"] = result
    _SCHEDULE_CACHE["timestamp"] = now
    return result


def invalidate_schedule_cache() -> None:
    _SCHEDULE_CACHE["data"] = None
    _SCHEDULE_CACHE["timestamp"] = None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/backend/forecast_schedule.test.py -v
```
Expected: greedy tests (6) pass always. OR-Tools tests skip if not installed (`SKIPPED [reason: ortools not installed]`).

- [ ] **Step 5: Commit**

```bash
git add app/backend/modules/ml/services/schedule_optimizer.py tests/backend/forecast_schedule.test.py
git commit -m "feat(c8): schedule optimizer (OR-Tools CP-SAT + greedy fallback) + tests"
```

---

## Task 5: Backend Endpoints + ortools Dependency

**Files:**
- Modify: `app/backend/requirements.txt`
- Modify: `app/backend/modules/ml/router.py`

- [ ] **Step 1: Add ortools to requirements.txt**

Open `app/backend/requirements.txt` and append after the last existing line:

```
# Forecasting & Optimization (C8)
ortools>=9.7
```

- [ ] **Step 2: Add forecast cache + guard + 6 endpoints to router.py**

In `app/backend/modules/ml/router.py`, add after the existing `_BACKEND_MODELS`/`_MICRO_MODELS` constants (around line 34):

```python
# ── C8 Forecast cache ──────────────────────────────────────────────────────
_FORECAST_SUMMARY_CACHE: dict = {"data": None, "ts": None, "ttl": 1800}
```

Then add the `_require_planner` helper and the 6 endpoints at the **end of the file** (before the final line if any, or just append):

```python
# ── C8 helpers ─────────────────────────────────────────────────────────────

def _require_planner(current_user: Utilisateurs) -> None:
    """Allow CHEFTECH or ADMIN only."""
    if not current_user.role or current_user.role.value not in ("CHEFTECH", "ADMIN"):
        raise HTTPException(status_code=403, detail="Accès réservé aux planificateurs.")

_VALID_HORIZONS = {7, 30, 60}


# ── C8 Forecast Endpoints ──────────────────────────────────────────────────

@router.get("/forecast/summary")
async def get_forecast_summary(
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
) -> dict:
    """3 KPI cards for all roles — 30-day horizon, cached 30 min."""
    from .services.downtime_forecast import compute_fleet_downtime
    from .services.labor_forecast import forecast_labor
    from .services.budget_forecast import forecast_budget
    from .services.demand_forecast import compute_demand_forecast
    from models.utilisateurs import Utilisateurs as U

    now = datetime.utcnow()
    if (
        _FORECAST_SUMMARY_CACHE["data"] is not None
        and _FORECAST_SUMMARY_CACHE["ts"] is not None
        and (now - _FORECAST_SUMMARY_CACHE["ts"]).total_seconds() < _FORECAST_SUMMARY_CACHE["ttl"]
    ):
        return _FORECAST_SUMMARY_CACHE["data"]

    downtime = await compute_fleet_downtime(db, horizon_days=30)

    # technician count
    tech_res = await db.execute(select(U).where(U.role == "TECHNICIEN"))
    tech_count = len(tech_res.scalars().all())

    # open WOs count
    open_wo_res = await db.execute(
        select(func.count()).select_from(Ordres_travail).where(
            Ordres_travail.statut.in_([OrdreStatut.PLANIFIE, OrdreStatut.EN_COURS])
        )
    )
    open_wo_count = open_wo_res.scalar_one() or 0

    labor = forecast_labor(
        machine_forecasts=downtime["machines"],
        open_wo_count=open_wo_count,
        avg_wo_hours=4.0,
        technician_count=tech_count,
        horizon_days=30,
    )

    demand_data = await compute_demand_forecast(db, horizon_days=60, limit=50)
    budget = forecast_budget(
        labor_demand_hours=labor["demand_hours"],
        parts_reorder_items=demand_data.get("items", []),
    )

    payload = {
        "downtime_hours": downtime["total_expected_hours"],
        "labor_demand_hours": labor["demand_hours"],
        "labor_overload": labor["overload"],
        "budget_total": budget["total"],
        "currency": "EUR",
        "horizon_days": 30,
        "generated_at": now.isoformat(),
    }
    _FORECAST_SUMMARY_CACHE["data"] = payload
    _FORECAST_SUMMARY_CACHE["ts"] = now
    return payload


@router.get("/forecast/downtime")
async def get_forecast_downtime(
    horizon: int = Query(30, description="7, 30 or 60"),
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
) -> dict:
    """Per-machine downtime forecast. CHEFTECH + ADMIN only."""
    _require_planner(current_user)
    if horizon not in _VALID_HORIZONS:
        raise HTTPException(400, detail="horizon must be 7, 30 or 60")
    from .services.downtime_forecast import compute_fleet_downtime
    return await compute_fleet_downtime(db, horizon_days=horizon)


@router.get("/forecast/labor")
async def get_forecast_labor(
    horizon: int = Query(30, description="7, 30 or 60"),
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
) -> dict:
    """Labor demand vs capacity. CHEFTECH + ADMIN only."""
    _require_planner(current_user)
    if horizon not in _VALID_HORIZONS:
        raise HTTPException(400, detail="horizon must be 7, 30 or 60")
    from .services.downtime_forecast import compute_fleet_downtime
    from .services.labor_forecast import forecast_labor
    from models.utilisateurs import Utilisateurs as U

    downtime = await compute_fleet_downtime(db, horizon_days=horizon)
    tech_res = await db.execute(select(U).where(U.role == "TECHNICIEN"))
    tech_count = len(tech_res.scalars().all())
    open_wo_res = await db.execute(
        select(func.count()).select_from(Ordres_travail).where(
            Ordres_travail.statut.in_([OrdreStatut.PLANIFIE, OrdreStatut.EN_COURS])
        )
    )
    open_wo_count = open_wo_res.scalar_one() or 0
    return forecast_labor(downtime["machines"], open_wo_count, 4.0, tech_count, horizon)


@router.get("/forecast/budget")
async def get_forecast_budget(
    horizon: int = Query(30, description="7, 30 or 60"),
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
) -> dict:
    """Cost breakdown. CHEFTECH + ADMIN only."""
    _require_planner(current_user)
    if horizon not in _VALID_HORIZONS:
        raise HTTPException(400, detail="horizon must be 7, 30 or 60")
    from .services.downtime_forecast import compute_fleet_downtime
    from .services.labor_forecast import forecast_labor
    from .services.budget_forecast import forecast_budget
    from .services.demand_forecast import compute_demand_forecast
    from models.utilisateurs import Utilisateurs as U

    downtime = await compute_fleet_downtime(db, horizon_days=horizon)
    tech_res = await db.execute(select(U).where(U.role == "TECHNICIEN"))
    tech_count = len(tech_res.scalars().all())
    open_wo_res = await db.execute(
        select(func.count()).select_from(Ordres_travail).where(
            Ordres_travail.statut.in_([OrdreStatut.PLANIFIE, OrdreStatut.EN_COURS])
        )
    )
    open_wo_count = open_wo_res.scalar_one() or 0
    labor = forecast_labor(downtime["machines"], open_wo_count, 4.0, tech_count, horizon)
    demand_data = await compute_demand_forecast(db, horizon_days=horizon, limit=50)
    return forecast_budget(labor["demand_hours"], demand_data.get("items", []))


@router.post("/forecast/optimize-schedule")
async def post_optimize_schedule(
    horizon: int = Query(30, description="7, 30 or 60"),
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
) -> dict:
    """Trigger OR-Tools schedule optimizer. CHEFTECH + ADMIN only. Cached 30 min."""
    _require_planner(current_user)
    if horizon not in _VALID_HORIZONS:
        raise HTTPException(400, detail="horizon must be 7, 30 or 60")
    from .services.schedule_optimizer import compute_schedule
    return await compute_schedule(db, horizon_days=horizon)


@router.get("/forecast/my-schedule")
async def get_my_schedule(
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(get_current_user),
) -> dict:
    """TECHNICIEN: returns their own assignments from the cached schedule."""
    from .services.schedule_optimizer import compute_schedule
    schedule = await compute_schedule(db, horizon_days=30)
    my_assignments = [
        a for a in schedule.get("assignments", [])
        if a.get("technician_id") == current_user.id
    ]
    return {
        "assignments": my_assignments,
        "technician_id": current_user.id,
        "solved": schedule.get("solved"),
        "fallback": schedule.get("fallback"),
    }
```

- [ ] **Step 3: Verify router imports compile**

```bash
cd C:/Users/Admin/Downloads/EAM/EAMSagemCom/app/backend
python -c "from modules.ml.router import router; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Run all backend tests**

```bash
python -m pytest tests/backend/ -v --tb=short 2>&1 | tail -20
```
Expected: all existing tests still pass + new forecast tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/backend/requirements.txt app/backend/modules/ml/router.py
git commit -m "feat(c8): 6 forecast endpoints + ortools dep"
```

---

## Task 6: ForecastSummaryTile + Dashboard Embed

**Files:**
- Create: `app/frontend/src/modules/shared/dashboard/ForecastSummaryTile.tsx`
- Create: `app/frontend/src/modules/cheftech/forecast/forecastTransforms.test.ts`
- Modify: `app/frontend/src/modules/cheftech/CheftechDashboard.tsx`

- [ ] **Step 1: Write the failing vitest test**

```typescript
// app/frontend/src/modules/cheftech/forecast/forecastTransforms.test.ts
import { describe, it, expect } from 'vitest';
import { formatHours, formatCurrency, labelOverload } from './forecastTransforms';

describe('formatHours', () => {
  it('formats zero', () => expect(formatHours(0)).toBe('0 h'));
  it('rounds to 1 decimal', () => expect(formatHours(12.567)).toBe('12.6 h'));
  it('formats large number', () => expect(formatHours(100)).toBe('100 h'));
});

describe('formatCurrency', () => {
  it('formats euros', () => expect(formatCurrency(1500)).toContain('1'));
  it('returns string', () => expect(typeof formatCurrency(50)).toBe('string'));
});

describe('labelOverload', () => {
  it('overload true → warning label', () => expect(labelOverload(true)).toContain('!'));
  it('overload false → ok label', () => expect(labelOverload(false)).not.toContain('!'));
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd C:/Users/Admin/Downloads/EAM/EAMSagemCom/app/frontend
npx vitest run src/modules/cheftech/forecast/forecastTransforms.test.ts 2>&1 | tail -10
```
Expected: error (module not found)

- [ ] **Step 3: Create forecastTransforms.ts**

```typescript
// app/frontend/src/modules/cheftech/forecast/forecastTransforms.ts
export function formatHours(h: number): string {
  return `${Math.round(h * 10) / 10} h`;
}

export function formatCurrency(eur: number): string {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(eur);
}

export function labelOverload(overload: boolean): string {
  return overload ? '⚠ Capacité dépassée !' : 'Capacité suffisante';
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
npx vitest run src/modules/cheftech/forecast/forecastTransforms.test.ts
```
Expected: 5 passed

- [ ] **Step 5: Create ForecastSummaryTile.tsx**

```tsx
// app/frontend/src/modules/shared/dashboard/ForecastSummaryTile.tsx
import { useEffect, useState } from 'react';
import { TrendingDown, Clock, Banknote, AlertTriangle } from 'lucide-react';
import { formatHours, formatCurrency } from '@/modules/cheftech/forecast/forecastTransforms';

const API = import.meta.env.VITE_API_BASE_URL || '';
const token = () => localStorage.getItem('access_token');

interface ForecastSummary {
  downtime_hours: number;
  labor_demand_hours: number;
  labor_overload: boolean;
  budget_total: number;
  currency: string;
}

export function ForecastSummaryTile() {
  const [data, setData] = useState<ForecastSummary | null>(null);

  useEffect(() => {
    fetch(`${API}/api/v1/ml/forecast/summary`, {
      headers: { Authorization: `Bearer ${token()}` },
    })
      .then(r => r.ok ? r.json() : null)
      .then(j => j && setData(j))
      .catch(() => {});
  }, []);

  if (!data) return <div className="h-20 rounded-lg bg-slate-800 animate-pulse col-span-3" />;

  const tiles = [
    {
      icon: <TrendingDown className="h-4 w-4 text-red-400" />,
      label: 'Temps d\'arrêt prévu (30j)',
      value: formatHours(data.downtime_hours),
      accent: data.downtime_hours > 40 ? 'text-red-300' : 'text-slate-100',
    },
    {
      icon: <Clock className="h-4 w-4 text-amber-400" />,
      label: 'Main-d\'œuvre requise (30j)',
      value: formatHours(data.labor_demand_hours),
      accent: data.labor_overload ? 'text-amber-300' : 'text-slate-100',
      badge: data.labor_overload ? (
        <span className="ml-2 inline-flex items-center gap-1 text-xs text-amber-400 bg-amber-900/40 rounded px-1.5 py-0.5">
          <AlertTriangle className="h-3 w-3" /> Surcharge
        </span>
      ) : null,
    },
    {
      icon: <Banknote className="h-4 w-4 text-blue-400" />,
      label: 'Budget maintenance estimé',
      value: formatCurrency(data.budget_total),
      accent: 'text-slate-100',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      {tiles.map(t => (
        <div key={t.label} className="rounded-lg border border-slate-700 bg-slate-800/60 px-4 py-3 flex items-start gap-3">
          <div className="mt-0.5">{t.icon}</div>
          <div>
            <p className="text-xs text-slate-400">{t.label}</p>
            <p className={`text-lg font-semibold mt-0.5 ${t.accent}`}>
              {t.value}{t.badge}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 6: Embed ForecastSummaryTile in CheftechDashboard.tsx**

In `app/frontend/src/modules/cheftech/CheftechDashboard.tsx`:

Add import at top (after existing imports):
```tsx
import { ForecastSummaryTile } from '@/modules/shared/dashboard/ForecastSummaryTile';
```

Find the block that contains `<NextBestActions` and add `<ForecastSummaryTile />` immediately after it:
```tsx
          <BriefingBar />
          <NextBestActions
            // ... existing props
          />
          <ForecastSummaryTile />   {/* ← add this line */}
```

- [ ] **Step 7: Run vitest suite**

```bash
npx vitest run 2>&1 | tail -5
```
Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add app/frontend/src/modules/shared/dashboard/ForecastSummaryTile.tsx \
        app/frontend/src/modules/cheftech/forecast/forecastTransforms.ts \
        app/frontend/src/modules/cheftech/forecast/forecastTransforms.test.ts \
        app/frontend/src/modules/cheftech/CheftechDashboard.tsx
git commit -m "feat(c8): ForecastSummaryTile + dashboard embed"
```

---

## Task 7: MachineForecastPanel + MachineDetailPage Tab

**Files:**
- Create: `app/frontend/src/modules/shared/machines/components/MachineForecastPanel.tsx`
- Modify: `app/frontend/src/modules/shared/MachineDetailPage.tsx`

- [ ] **Step 1: Create MachineForecastPanel.tsx**

```tsx
// app/frontend/src/modules/shared/machines/components/MachineForecastPanel.tsx
import { useEffect, useState } from 'react';
import { TrendingDown, Clock } from 'lucide-react';
import { formatHours } from '@/modules/cheftech/forecast/forecastTransforms';

const API = import.meta.env.VITE_API_BASE_URL || '';
const token = () => localStorage.getItem('access_token');

interface MachineDowntime {
  machine_id: number;
  machine_name: string;
  p_failure: number;
  expected_downtime_hours: number;
  horizon_days: number;
}

interface Props { machineId: number }

export function MachineForecastPanel({ machineId }: Props) {
  const [data, setData] = useState<MachineDowntime | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${API}/api/v1/ml/forecast/downtime?horizon=30`, {
      headers: { Authorization: `Bearer ${token()}` },
    })
      .then(r => r.ok ? r.json() : null)
      .then(j => {
        if (!j) return;
        const machine = j.machines?.find((m: MachineDowntime) => m.machine_id === machineId);
        if (machine) setData(machine);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [machineId]);

  if (loading) return <div className="h-28 rounded-lg bg-slate-800 animate-pulse" />;
  if (!data) return (
    <div className="rounded-lg border border-slate-700 bg-slate-800/40 px-4 py-3 text-xs text-slate-400">
      Données de prévision non disponibles.
    </div>
  );

  const pct = Math.round(data.p_failure * 100);
  const riskColor = pct >= 70 ? 'text-red-400' : pct >= 40 ? 'text-amber-400' : 'text-emerald-400';

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800/60 p-4 space-y-3">
      <p className="text-xs font-semibold text-blue-300 uppercase tracking-wider">Prévision 30 jours</p>
      <div className="grid grid-cols-2 gap-4">
        <div className="flex items-start gap-2">
          <TrendingDown className="h-4 w-4 text-red-400 mt-0.5" />
          <div>
            <p className="text-xs text-slate-400">Probabilité de panne</p>
            <p className={`text-xl font-bold mt-0.5 ${riskColor}`}>{pct}%</p>
          </div>
        </div>
        <div className="flex items-start gap-2">
          <Clock className="h-4 w-4 text-amber-400 mt-0.5" />
          <div>
            <p className="text-xs text-slate-400">Arrêt attendu</p>
            <p className="text-xl font-bold text-slate-100 mt-0.5">{formatHours(data.expected_downtime_hours)}</p>
          </div>
        </div>
      </div>
      <div className="h-1.5 rounded-full bg-slate-700">
        <div
          className={`h-1.5 rounded-full ${pct >= 70 ? 'bg-red-500' : pct >= 40 ? 'bg-amber-500' : 'bg-emerald-500'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add "Prévisions" tab to MachineDetailPage.tsx**

In `app/frontend/src/modules/shared/MachineDetailPage.tsx`:

Add import after the existing component imports (around line 42–46):
```tsx
import { MachineForecastPanel } from './machines/components/MachineForecastPanel';
```

Find the `<TabsList className="grid grid-cols-4 ...">` (around line 308) and change it to `grid-cols-5`:
```tsx
<TabsList className="grid grid-cols-5 w-full max-w-2xl">
```

Add the new trigger after the existing 4 triggers (after line 320 `</TabsTrigger>`):
```tsx
  <TabTrigger value="forecast" className="flex items-center gap-1.5 text-sm">
    <TrendingDown className="h-4 w-4" /> Prévisions
  </TabTrigger>
```

Note: `TrendingDown` must be added to the existing lucide-react import at the top of the file.

Add the TabsContent after the last existing one (after line 414):
```tsx
<TabsContent value="forecast" className="mt-4">
  {machine && <MachineForecastPanel machineId={machine.id} />}
</TabsContent>
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd C:/Users/Admin/Downloads/EAM/EAMSagemCom/app/frontend
npx tsc --noEmit 2>&1 | head -20
```
Expected: 0 errors

- [ ] **Step 4: Commit**

```bash
git add app/frontend/src/modules/shared/machines/components/MachineForecastPanel.tsx \
        app/frontend/src/modules/shared/MachineDetailPage.tsx
git commit -m "feat(c8): MachineForecastPanel + machine detail Prévisions tab"
```

---

## Task 8: Forecast Charts (Downtime + Labor + Budget)

**Files:**
- Create: `app/frontend/src/modules/cheftech/forecast/DowntimeForecastChart.tsx`
- Create: `app/frontend/src/modules/cheftech/forecast/LaborForecastChart.tsx`
- Create: `app/frontend/src/modules/cheftech/forecast/BudgetForecastCard.tsx`

- [ ] **Step 1: Create DowntimeForecastChart.tsx**

```tsx
// app/frontend/src/modules/cheftech/forecast/DowntimeForecastChart.tsx
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface MachineDowntime {
  machine_name: string;
  p_failure: number;
  expected_downtime_hours: number;
}

interface Props {
  machines: MachineDowntime[];
}

function riskColor(p: number): string {
  if (p >= 0.7) return '#f87171';   // red-400
  if (p >= 0.4) return '#fbbf24';   // amber-400
  return '#34d399';                  // emerald-400
}

export function DowntimeForecastChart({ machines }: Props) {
  const data = machines.slice(0, 10).map(m => ({
    name: m.machine_name.length > 14 ? m.machine_name.slice(0, 14) + '…' : m.machine_name,
    heures: m.expected_downtime_hours,
    p: m.p_failure,
  }));

  if (!data.length) return (
    <div className="h-40 flex items-center justify-center text-slate-400 text-sm">Aucune donnée</div>
  );

  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold text-blue-300 uppercase tracking-wider">Arrêts attendus par machine</p>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
          <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} unit=" h" />
          <YAxis dataKey="name" type="category" tick={{ fill: '#cbd5e1', fontSize: 11 }} width={110} />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
            formatter={(v: number) => [`${v.toFixed(1)} h`, 'Arrêt attendu']}
          />
          <Bar dataKey="heures" radius={[0, 4, 4, 0]}>
            {data.map((d, i) => <Cell key={i} fill={riskColor(d.p)} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 2: Create LaborForecastChart.tsx**

```tsx
// app/frontend/src/modules/cheftech/forecast/LaborForecastChart.tsx
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { AlertTriangle } from 'lucide-react';
import { formatHours } from './forecastTransforms';

interface LaborData {
  demand_hours: number;
  capacity_hours: number;
  coverage_pct: number;
  overload: boolean;
  technician_count: number;
  workdays: number;
  breakdown: { predicted_failure_hours: number; open_wo_backlog_hours: number };
}

interface Props { data: LaborData; horizon: number }

export function LaborForecastChart({ data, horizon }: Props) {
  const chartData = [
    { name: `${horizon}j`, demande: data.demand_hours, capacité: data.capacity_hours },
  ];

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-blue-300 uppercase tracking-wider">Main-d'œuvre</p>
        {data.overload && (
          <span className="inline-flex items-center gap-1 text-xs text-amber-400 bg-amber-900/40 rounded px-2 py-0.5">
            <AlertTriangle className="h-3 w-3" /> Surcharge prévue
          </span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={140}>
        <BarChart data={chartData}>
          <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} unit=" h" />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
            formatter={(v: number) => [`${v.toFixed(0)} h`]}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="demande" fill="#f87171" radius={[4, 4, 0, 0]} />
          <Bar dataKey="capacité" fill="#34d399" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <div className="grid grid-cols-3 gap-2 text-center mt-1">
        <div className="rounded bg-slate-800 p-2">
          <p className="text-[10px] text-slate-400">Demande</p>
          <p className="text-sm font-bold text-red-300">{formatHours(data.demand_hours)}</p>
        </div>
        <div className="rounded bg-slate-800 p-2">
          <p className="text-[10px] text-slate-400">Capacité</p>
          <p className="text-sm font-bold text-emerald-300">{formatHours(data.capacity_hours)}</p>
        </div>
        <div className="rounded bg-slate-800 p-2">
          <p className="text-[10px] text-slate-400">Couverture</p>
          <p className={`text-sm font-bold ${data.overload ? 'text-amber-300' : 'text-emerald-300'}`}>
            {data.coverage_pct}%
          </p>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create BudgetForecastCard.tsx**

```tsx
// app/frontend/src/modules/cheftech/forecast/BudgetForecastCard.tsx
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { formatCurrency } from './forecastTransforms';

interface BudgetData {
  labor_cost: number;
  parts_cost: number;
  total: number;
  currency: string;
  breakdown: { label: string; value: number }[];
}

interface Props { data: BudgetData }

const COLORS = ['#60a5fa', '#f59e0b'];

export function BudgetForecastCard({ data }: Props) {
  const pieData = data.breakdown.filter(b => b.value > 0);

  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold text-blue-300 uppercase tracking-wider">Budget estimé</p>
      <div className="flex items-center gap-4">
        {pieData.length > 0 ? (
          <ResponsiveContainer width={120} height={120}>
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="label" cx="50%" cy="50%" outerRadius={50} innerRadius={30}>
                {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                formatter={(v: number) => [formatCurrency(v)]}
              />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="w-[120px] h-[120px] flex items-center justify-center text-xs text-slate-500">—</div>
        )}
        <div className="flex-1 space-y-2">
          {data.breakdown.map((b, i) => (
            <div key={b.label} className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-xs text-slate-300">
                <span className="w-2 h-2 rounded-full inline-block" style={{ background: COLORS[i % COLORS.length] }} />
                {b.label}
              </span>
              <span className="text-sm font-semibold text-slate-100">{formatCurrency(b.value)}</span>
            </div>
          ))}
          <div className="border-t border-slate-700 pt-2 flex justify-between">
            <span className="text-xs text-slate-300 font-semibold">Total</span>
            <span className="text-base font-bold text-blue-300">{formatCurrency(data.total)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Verify TypeScript**

```bash
npx tsc --noEmit 2>&1 | head -20
```
Expected: 0 errors

- [ ] **Step 5: Commit**

```bash
git add app/frontend/src/modules/cheftech/forecast/DowntimeForecastChart.tsx \
        app/frontend/src/modules/cheftech/forecast/LaborForecastChart.tsx \
        app/frontend/src/modules/cheftech/forecast/BudgetForecastCard.tsx
git commit -m "feat(c8): downtime/labor/budget forecast chart components"
```

---

## Task 9: Schedule Optimizer Panel + Technician Schedule View

**Files:**
- Create: `app/frontend/src/modules/cheftech/forecast/ScheduleOptimizerPanel.tsx`
- Create: `app/frontend/src/modules/cheftech/forecast/TechnicianScheduleView.tsx`

- [ ] **Step 1: Create ScheduleOptimizerPanel.tsx**

```tsx
// app/frontend/src/modules/cheftech/forecast/ScheduleOptimizerPanel.tsx
import { useState } from 'react';
import { Calendar, RefreshCw, AlertTriangle, Info } from 'lucide-react';

const API = import.meta.env.VITE_API_BASE_URL || '';
const token = () => localStorage.getItem('access_token');

interface Assignment {
  wo_id: number;
  titre: string;
  technician_id: number;
  start_day: number;
  end_day: number;
}

interface ScheduleResult {
  assignments: Assignment[];
  makespan_days: number;
  solved: boolean;
  fallback: boolean;
}

interface Props { horizon: number }

export function ScheduleOptimizerPanel({ horizon }: Props) {
  const [result, setResult] = useState<ScheduleResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleOptimize = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch(`${API}/api/v1/ml/forecast/optimize-schedule?horizon=${horizon}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token()}` },
      });
      if (!r.ok) throw new Error(`Erreur ${r.status}`);
      setResult(await r.json());
    } catch (e: any) {
      setError(e.message ?? 'Erreur inconnue');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-blue-300 uppercase tracking-wider">Optimiseur de planning</p>
        <button
          onClick={handleOptimize}
          disabled={loading}
          className="inline-flex items-center gap-2 text-xs font-medium text-blue-200 bg-slate-800 border border-slate-700 rounded-md px-3 py-1.5 hover:bg-slate-700/60 disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          {loading ? 'Optimisation…' : 'Optimiser le planning'}
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded bg-red-950 border border-red-800 px-3 py-2 text-xs text-red-300">
          <AlertTriangle className="h-3.5 w-3.5" /> {error}
        </div>
      )}

      {result && (
        <div className="space-y-2">
          {result.fallback && (
            <div className="flex items-center gap-2 rounded bg-amber-950 border border-amber-800 px-3 py-2 text-xs text-amber-300">
              <Info className="h-3.5 w-3.5" /> Mode simplifié — solveur OR-Tools non disponible.
            </div>
          )}
          {!result.solved && (
            <div className="flex items-center gap-2 rounded bg-amber-950 border border-amber-800 px-3 py-2 text-xs text-amber-300">
              <AlertTriangle className="h-3.5 w-3.5" /> Solution partielle — délai de résolution dépassé.
            </div>
          )}
          <p className="text-xs text-slate-400">
            {result.assignments.length} ordre(s) planifié(s) · Durée totale : {result.makespan_days}j
          </p>
          <div className="rounded-lg border border-slate-700 overflow-hidden">
            <table className="w-full text-xs">
              <thead className="bg-slate-800 text-blue-300">
                <tr>
                  <th className="text-left px-3 py-2">Ordre</th>
                  <th className="text-left px-3 py-2">Technicien</th>
                  <th className="text-left px-3 py-2">Début (J)</th>
                  <th className="text-left px-3 py-2">Fin (J)</th>
                </tr>
              </thead>
              <tbody>
                {result.assignments.map(a => (
                  <tr key={a.wo_id} className="border-t border-slate-800">
                    <td className="px-3 py-2 text-slate-200">{a.titre || `OT #${a.wo_id}`}</td>
                    <td className="px-3 py-2 text-slate-300">#{a.technician_id}</td>
                    <td className="px-3 py-2 text-slate-300">J+{a.start_day}</td>
                    <td className="px-3 py-2 text-slate-300">J+{a.end_day}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!result && !loading && (
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <Calendar className="h-4 w-4" />
          Cliquez sur "Optimiser" pour répartir les ordres de travail ouverts entre les techniciens.
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Create TechnicianScheduleView.tsx**

```tsx
// app/frontend/src/modules/cheftech/forecast/TechnicianScheduleView.tsx
import { useEffect, useState } from 'react';
import { Calendar, Info } from 'lucide-react';

const API = import.meta.env.VITE_API_BASE_URL || '';
const token = () => localStorage.getItem('access_token');

interface Assignment {
  wo_id: number;
  titre: string;
  start_day: number;
  end_day: number;
}

interface MySchedule {
  assignments: Assignment[];
  technician_id: number;
  solved: boolean;
  fallback: boolean;
}

export function TechnicianScheduleView() {
  const [data, setData] = useState<MySchedule | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/v1/ml/forecast/my-schedule`, {
      headers: { Authorization: `Bearer ${token()}` },
    })
      .then(r => r.ok ? r.json() : null)
      .then(j => j && setData(j))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="h-40 rounded-lg bg-slate-800 animate-pulse" />;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-bold text-white">Mon planning</h2>
        <p className="text-sm text-blue-300 mt-1">Ordres de travail qui vous sont assignés (30 jours)</p>
      </div>

      {data?.fallback && (
        <div className="flex items-center gap-2 rounded bg-slate-800 border border-slate-700 px-3 py-2 text-xs text-slate-400">
          <Info className="h-3.5 w-3.5" /> Planning généré en mode simplifié.
        </div>
      )}

      {!data || data.assignments.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-slate-400 gap-2">
          <Calendar className="h-8 w-8" />
          <p className="text-sm">Aucun ordre de travail planifié pour le moment.</p>
          <p className="text-xs text-slate-500">Votre chef technique doit d'abord lancer l'optimisation du planning.</p>
        </div>
      ) : (
        <div className="rounded-lg border border-slate-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-800 text-blue-300 text-xs">
              <tr>
                <th className="text-left px-4 py-2">Ordre de travail</th>
                <th className="text-left px-4 py-2">Début prévu</th>
                <th className="text-left px-4 py-2">Fin prévue</th>
                <th className="text-left px-4 py-2">Durée</th>
              </tr>
            </thead>
            <tbody>
              {data.assignments.map(a => (
                <tr key={a.wo_id} className="border-t border-slate-800">
                  <td className="px-4 py-3 text-slate-100 font-medium">{a.titre || `OT #${a.wo_id}`}</td>
                  <td className="px-4 py-3 text-slate-300">J+{a.start_day}</td>
                  <td className="px-4 py-3 text-slate-300">J+{a.end_day}</td>
                  <td className="px-4 py-3 text-slate-300">{a.end_day - a.start_day}j</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Verify TypeScript**

```bash
npx tsc --noEmit 2>&1 | head -20
```
Expected: 0 errors

- [ ] **Step 4: Commit**

```bash
git add app/frontend/src/modules/cheftech/forecast/ScheduleOptimizerPanel.tsx \
        app/frontend/src/modules/cheftech/forecast/TechnicianScheduleView.tsx
git commit -m "feat(c8): schedule optimizer panel + technician schedule view"
```

---

## Task 10: ForecastDashboard + Route Wiring

**Files:**
- Create: `app/frontend/src/modules/cheftech/forecast/ForecastDashboard.tsx`
- Modify: `app/frontend/src/app/routing/AppRoutes.tsx`

- [ ] **Step 1: Create ForecastDashboard.tsx**

```tsx
// app/frontend/src/modules/cheftech/forecast/ForecastDashboard.tsx
import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { DowntimeForecastChart } from './DowntimeForecastChart';
import { LaborForecastChart } from './LaborForecastChart';
import { BudgetForecastCard } from './BudgetForecastCard';
import { ScheduleOptimizerPanel } from './ScheduleOptimizerPanel';
import { TechnicianScheduleView } from './TechnicianScheduleView';

const API = import.meta.env.VITE_API_BASE_URL || '';
const token = () => localStorage.getItem('access_token');

type Horizon = 7 | 30 | 60;

function useApi<T>(path: string, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    setLoading(true);
    fetch(`${API}${path}`, { headers: { Authorization: `Bearer ${token()}` } })
      .then(r => r.ok ? r.json() : null)
      .then(j => j && setData(j))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, deps);
  return { data, loading };
}

export default function ForecastDashboard() {
  const { user } = useAuth();
  const role = (user as any)?.role ?? '';
  const isTech = role === 'TECHNICIEN';
  const [horizon, setHorizon] = useState<Horizon>(30);

  const downtime = useApi<any>(`/api/v1/ml/forecast/downtime?horizon=${horizon}`, [horizon]);
  const labor = useApi<any>(`/api/v1/ml/forecast/labor?horizon=${horizon}`, [horizon]);
  const budget = useApi<any>(`/api/v1/ml/forecast/budget?horizon=${horizon}`, [horizon]);

  if (isTech) return <TechnicianScheduleView />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-white">Prévisions & Optimisation</h2>
          <p className="text-sm text-blue-300 mt-1">Horizon court terme — arrêts, charge, budget.</p>
        </div>
        <div className="flex rounded-lg border border-slate-700 overflow-hidden">
          {([7, 30, 60] as Horizon[]).map(h => (
            <button
              key={h}
              onClick={() => setHorizon(h)}
              className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                horizon === h
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
            >
              {h}j
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Downtime */}
        <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-5">
          {downtime.loading
            ? <div className="h-52 animate-pulse bg-slate-800 rounded" />
            : downtime.data && <DowntimeForecastChart machines={downtime.data.machines ?? []} />}
        </div>

        {/* Labor */}
        <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-5">
          {labor.loading
            ? <div className="h-52 animate-pulse bg-slate-800 rounded" />
            : labor.data && <LaborForecastChart data={labor.data} horizon={horizon} />}
        </div>

        {/* Budget */}
        <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-5">
          {budget.loading
            ? <div className="h-40 animate-pulse bg-slate-800 rounded" />
            : budget.data && <BudgetForecastCard data={budget.data} />}
        </div>

        {/* Optimizer */}
        <div className="rounded-xl border border-slate-700 bg-slate-800/40 p-5">
          <ScheduleOptimizerPanel horizon={horizon} />
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add /forecast route to AppRoutes.tsx**

In `app/frontend/src/app/routing/AppRoutes.tsx`:

Add import after the existing RAGDocuments import (around line 62):
```tsx
import ForecastDashboard from '@/modules/cheftech/forecast/ForecastDashboard';
```

Add route before the final `<Route path="*" ...>` (around line 749):
```tsx
      <Route
        path="/forecast"
        element={
          <ProtectedRoute allowedRoles={['ADMIN', 'CHEFTECH', 'TECHNICIEN']}>
            <Layout>
              <ForecastDashboard />
            </Layout>
          </ProtectedRoute>
        }
      />
```

- [ ] **Step 3: Verify TypeScript**

```bash
npx tsc --noEmit 2>&1 | head -20
```
Expected: 0 errors

- [ ] **Step 4: Run full vitest suite**

```bash
npx vitest run 2>&1 | tail -10
```
Expected: all existing tests + new forecast transforms test pass.

- [ ] **Step 5: Run all backend tests**

```bash
cd C:/Users/Admin/Downloads/EAM/EAMSagemCom
python -m pytest tests/backend/ -v --tb=short 2>&1 | tail -20
```
Expected: all tests pass (new C8 tests included).

- [ ] **Step 6: Commit**

```bash
git add app/frontend/src/modules/cheftech/forecast/ForecastDashboard.tsx \
        app/frontend/src/app/routing/AppRoutes.tsx
git commit -m "feat(c8): ForecastDashboard page + /forecast route"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Downtime forecast service → Task 1
- [x] Labor forecast service → Task 2
- [x] Budget forecast service → Task 3
- [x] Schedule optimizer (OR-Tools + greedy) → Task 4
- [x] ortools dep → Task 5 (requirements.txt)
- [x] 6 backend endpoints → Task 5 (router.py)
- [x] Role guard `_require_planner` → Task 5
- [x] Caches (30 min TTL) → Tasks 1, 4, 5 (summary cache)
- [x] ForecastSummaryTile embed in CheftechDashboard → Task 6
- [x] MachineForecastPanel embed in MachineDetailPage → Task 7
- [x] DowntimeForecastChart → Task 8
- [x] LaborForecastChart → Task 8
- [x] BudgetForecastCard → Task 8
- [x] ScheduleOptimizerPanel (fallback badge) → Task 9
- [x] TechnicianScheduleView → Task 9
- [x] ForecastDashboard + horizon toggle → Task 10
- [x] /forecast route (ADMIN + CHEFTECH + TECHNICIEN) → Task 10
- [x] TECHNICIEN sees only TechnicianScheduleView → Task 10
- [x] forecastTransforms.test.ts → Task 6
- [x] OR-Tools importorskip pattern → Task 4

**No placeholders found.**

**Type consistency:**
- `estimate_downtime_hours` → defined Task 1, used Task 5 router ✓
- `forecast_labor` → defined Task 2, used Task 5 ✓
- `forecast_budget` → defined Task 3, used Task 5 ✓
- `_greedy_schedule` → defined Task 4, tested Task 4 ✓
- `optimize_schedule` → defined Task 4, async wrapper `compute_schedule` defined Task 4 ✓
- `ForecastSummaryTile` → created Task 6, imported Task 6 ✓
- `MachineForecastPanel` → created Task 7, imported Task 7 ✓
- `forecastTransforms.formatHours/formatCurrency/labelOverload` → defined Task 6, used Tasks 7-9 ✓
