# C8 Forecasting & Optimization Layer — Design Spec

> **For agentic workers:** Use `superpowers:writing-plans` to generate the implementation plan from this spec.

**Goal:** Add short-horizon (7/30/60-day) downtime, labor, and budget forecasts plus an OR-Tools schedule optimizer to the EAM platform, surfaced as dashboard embeds (all roles) and a dedicated `/forecast` page.

**Approach:** Approach 2 — Forecast services (pure, deterministic) + in-process OR-Tools CP-SAT optimizer running in asyncio thread pool with greedy fallback. No new microservice, no new DB migrations.

---

## 1. Architecture

```
Existing data sources
  MlPredictionLog  (rul_days, failure_probability, machine_id)
  Ordres_travail   (statut, date_debut, date_fin, priority, machine_id)
  Utilisateurs     (role=TECHNICIEN → capacity headcount)
  demand_forecast  (parts urgency + reorder items)
         │
         ▼
4 pure service files (app/backend/modules/ml/services/)
  downtime_forecast.py   — RUL + failure_prob → expected downtime hours per horizon
  labor_forecast.py      — downtime hours × avg WO duration → tech-hours demand/capacity
  budget_forecast.py     — labor cost + parts reorder cost → spend forecast
  schedule_optimizer.py  — OR-Tools CP-SAT: WOs × technicians → optimized assignments
         │
         ▼
ML router (existing) — 6 new endpoints
         │
    ┌────┴─────────────────────────┐
    ▼                              ▼
Dashboard embeds              /forecast page
  ForecastSummaryTile         ForecastDashboard (role-aware)
  MachineForecastPanel          DowntimeForecastChart
                                LaborForecastChart
                                BudgetForecastCard
                                ScheduleOptimizerPanel   (CHEFTECH+ADMIN)
                                TechnicianScheduleView   (TECHNICIEN)
```

---

## 2. Backend Services (Pure Functions)

### 2.1 `downtime_forecast.py`

**File:** `app/backend/modules/ml/services/downtime_forecast.py`

```python
def estimate_downtime_hours(
    rul_days: float,
    failure_prob: float,          # 0–100
    horizon_days: int,            # 7 | 30 | 60
    avg_repair_hours: float = 8.0,
) -> dict:
    """
    Returns {horizon_days, p_failure, expected_downtime_hours, confidence}
    p_failure blends RUL proximity and failure probability.
    confidence: 'high' | 'medium' | 'low' based on data freshness (not computed here — set by caller).
    """
    rul_factor = max(0.0, 1.0 - rul_days / max(horizon_days, 1))
    prob_factor = min(1.0, failure_prob / 100.0)
    p_failure = min(1.0, prob_factor * 0.6 + rul_factor * 0.4)
    expected = round(p_failure * avg_repair_hours, 2)
    return {
        "horizon_days": horizon_days,
        "p_failure": round(p_failure, 4),
        "expected_downtime_hours": expected,
    }


async def compute_fleet_downtime(db, horizon_days: int) -> dict:
    """Async wrapper: fetches latest MlPredictionLog per machine, calls estimate_downtime_hours."""
    # Returns {machines: [{machine_id, machine_name, ...estimate_result}], total_expected_hours, generated_at}
```

**avg_repair_hours**: computed from `Ordres_travail` where `date_debut` and `date_fin` both set; fallback 8.0h if no history.

---

### 2.2 `labor_forecast.py`

**File:** `app/backend/modules/ml/services/labor_forecast.py`

```python
def forecast_labor(
    machine_forecasts: list[dict],   # from downtime_forecast
    open_wo_count: int,
    avg_wo_hours: float,             # from WO history, fallback 4.0
    technician_count: int,
    horizon_days: int,
) -> dict:
    """
    Returns {demand_hours, capacity_hours, coverage_pct, overload, breakdown}
    capacity = technician_count × 8h × workdays(horizon_days)
    workdays ≈ horizon_days × 5/7
    """
    predicted_hours = sum(m["expected_downtime_hours"] for m in machine_forecasts)
    backlog_hours = open_wo_count * avg_wo_hours
    demand = round(predicted_hours + backlog_hours, 1)
    workdays = round(horizon_days * 5 / 7)
    capacity = technician_count * 8 * workdays
    coverage = round(min(100.0, capacity / max(demand, 0.01) * 100), 1)
    return {
        "demand_hours": demand,
        "capacity_hours": float(capacity),
        "coverage_pct": coverage,
        "overload": demand > capacity,
        "breakdown": {
            "predicted_failure_hours": round(predicted_hours, 1),
            "open_wo_backlog_hours": round(backlog_hours, 1),
        },
    }
```

---

### 2.3 `budget_forecast.py`

**File:** `app/backend/modules/ml/services/budget_forecast.py`

```python
LABOR_RATE_DEFAULT = 50.0  # €/hr — configurable via env var LABOR_RATE_EUR

def forecast_budget(
    labor_demand_hours: float,
    parts_reorder_items: list[dict],  # from demand_forecast items
    labor_rate: float = LABOR_RATE_DEFAULT,
) -> dict:
    """
    Returns {labor_cost, parts_cost, total, currency, breakdown[]}
    parts_cost: sum(reorder_qty_suggested × unit_price) — unit_price from Piece.unit_price if exists, else 0
    """
    labor_cost = round(labor_demand_hours * labor_rate, 2)
    parts_cost = round(
        sum(
            i.get("reorder_qty_suggested", 0) * i.get("unit_price", 0.0)
            for i in parts_reorder_items
        ),
        2,
    )
    return {
        "labor_cost": labor_cost,
        "parts_cost": parts_cost,
        "total": round(labor_cost + parts_cost, 2),
        "currency": "EUR",
        "breakdown": [
            {"label": "Main-d'œuvre", "value": labor_cost},
            {"label": "Pièces de rechange", "value": parts_cost},
        ],
    }
```

---

### 2.4 `schedule_optimizer.py`

**File:** `app/backend/modules/ml/services/schedule_optimizer.py`

```python
def optimize_schedule(
    work_orders: list[dict],      # [{id, priority(1-5), estimated_hours, parts_ready: bool}]
    technician_ids: list[int],
    horizon_days: int = 30,
    max_solve_seconds: int = 5,
) -> dict:
    """
    OR-Tools CP-SAT: minimize sum(priority × completion_day).
    WOs with parts_ready=False deferred +3 days minimum.
    Returns {assignments, makespan_days, solved, fallback}
    fallback=True when ortools unavailable → greedy round-robin.
    """
```

**CP-SAT model:**
- Variables: `start[wo]` (day index 0..horizon_days), `tech[wo]` (technician index)
- Constraint: each technician works ≤ 8h/day (bin-packing per day)
- Constraint: `parts_ready=False` → `start[wo] >= 3`
- Objective: minimize `sum(priority * (start[wo] + ceil(estimated_hours/8)))`
- Solver timeout: `max_solve_seconds`

**Greedy fallback** (no ortools dep):
- Sort WOs by priority desc, assign round-robin to technicians, start day = next available slot.

**Async wrapper:**
```python
async def compute_schedule(db, horizon_days: int) -> dict:
    # Fetch open WOs + technician IDs, run optimize_schedule in run_in_executor
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, optimize_schedule, wos, tech_ids, horizon_days)
    return result
```

---

## 3. API Endpoints

All added to `app/backend/modules/ml/router.py`. Auth via existing `get_current_user`.

| Method | Path | Guard | Returns |
|---|---|---|---|
| `GET` | `/api/v1/ml/forecast/summary` | Any auth | 3 KPIs (downtime_hours, labor_demand_hours, budget_total) — 30-day default |
| `GET` | `/api/v1/ml/forecast/downtime` | CHEFTECH\|ADMIN | Per-machine list + total, `?horizon=7\|30\|60` |
| `GET` | `/api/v1/ml/forecast/labor` | CHEFTECH\|ADMIN | demand/capacity/overload, `?horizon=7\|30\|60` |
| `GET` | `/api/v1/ml/forecast/budget` | CHEFTECH\|ADMIN | cost breakdown, `?horizon=7\|30\|60` |
| `POST` | `/api/v1/ml/forecast/optimize-schedule` | CHEFTECH\|ADMIN | Triggers OR-Tools, returns assignments (cached 30 min) |
| `GET` | `/api/v1/ml/forecast/my-schedule` | TECHNICIEN | Filters optimizer output to calling user's assignments |

**Role guard:**
```python
def _require_planner(user):
    if user.role.value not in ("CHEFTECH", "ADMIN"):
        raise HTTPException(status_code=403, detail="Planificateur requis")
```

**Cache:** In-memory dict keyed by `(type, horizon)`, TTL 30 min. Same pattern as `demand_forecast.py`.

**Horizon validation:**
```python
VALID_HORIZONS = {7, 30, 60}
if horizon not in VALID_HORIZONS:
    raise HTTPException(400, detail="horizon must be 7, 30, or 60")
```

---

## 4. Frontend Components

### 4.1 New files

```
app/frontend/src/modules/cheftech/forecast/
  ForecastDashboard.tsx          — /forecast route, role-aware layout
  DowntimeForecastChart.tsx      — recharts BarChart, per-machine p_failure
  LaborForecastChart.tsx         — stacked BarChart: demand vs capacity + overload badge
  BudgetForecastCard.tsx         — 3 tiles (labor / parts / total) or donut
  ScheduleOptimizerPanel.tsx     — "Optimiser" button + assignments table (CHEFTECH/ADMIN only)
  TechnicianScheduleView.tsx     — TECHNICIEN: own assignments from /my-schedule

app/frontend/src/modules/shared/dashboard/
  ForecastSummaryTile.tsx        — 3 KPI mini-cards, embed in ChefTech dashboard

app/frontend/src/modules/shared/machines/components/
  MachineForecastPanel.tsx       — single-machine 30-day outlook (downtime p_failure + labor)
```

### 4.2 Routing

Add `/forecast` route to `app/frontend/src/App.tsx` (or wherever routes are defined).
Nav link added to ChefTech + ADMIN sidebar. TECHNICIEN nav shows `/forecast` with label "Mon planning".

### 4.3 Role rendering in `ForecastDashboard`

```tsx
const isTech = role === 'TECHNICIEN'

return isTech
  ? <TechnicianScheduleView />
  : (
    <>
      <ForecastSummaryTile />
      <HorizonToggle />           {/* [7j | 30j | 60j] */}
      <DowntimeForecastChart />
      <LaborForecastChart />
      <BudgetForecastCard />
      <ScheduleOptimizerPanel />
    </>
  )
```

### 4.4 OR-Tools UX

`ScheduleOptimizerPanel`:
- Button: "Optimiser le planning" → POST `/optimize-schedule` → loading spinner
- On success: table of assignments (WO title | Technicien | Début | Fin)
- `fallback: true` response → amber badge: "Mode simplifié (solveur indisponible)"
- `solved: false` (timeout) → warning: "Solution partielle — délai dépassé"

### 4.5 Data fetching

Raw `fetch` + Bearer token from `localStorage.getItem('access_token')` — matches existing pattern (WhyDrawer, ModelHealthTable).

---

## 5. Testing

### Backend (`tests/backend/`)

| File | Key cases |
|---|---|
| `forecast_downtime.test.py` | `rul=5, prob=80, horizon=30` → high p_failure; `rul=200, prob=5` → low; horizon 7/30/60 all valid |
| `forecast_labor.test.py` | `demand > capacity` → `overload=True`; `coverage_pct` clamps 0–100; zero technicians → graceful |
| `forecast_budget.test.py` | `parts_reorder_items=[]` → `parts_cost=0`; labor rate env var override |
| `schedule_optimizer.test.py` | Greedy fallback returns valid assignments (always runs); OR-Tools path via `pytest.importorskip("ortools")` |

### Frontend (vitest)

| File | Key cases |
|---|---|
| `forecastTransforms.test.ts` | horizon filter, role filter, KPI number formatting (e.g. `1234 → "1 234 h"`) |

**OR-Tools skip pattern:**
```python
ortools = pytest.importorskip("ortools", reason="ortools not installed — skipping CP-SAT path")
```

Greedy fallback is always tested regardless of ortools presence.

---

## 6. Dependencies

| Dep | Where | Already present? |
|---|---|---|
| `ortools` | `app/backend/requirements.txt` | No — add |
| `recharts` | frontend | Yes |
| `asyncio` | stdlib | Yes |

`ortools` install: `ortools>=9.7` (Python package — ~50MB but pure Python wheels available).

---

## 7. Non-Goals (YAGNI)

- Dedicated forecast microservice
- Gantt chart UI (separate B-series feature)
- Inventory reorder automation (separate from procurement draft — P7.4 already handles)
- Annual / CapEx horizon (out of 7/30/60 scope)
- Real-time WebSocket updates
- Multi-site aggregation

---

## 8. File Change Summary

**Create:**
- `app/backend/modules/ml/services/downtime_forecast.py`
- `app/backend/modules/ml/services/labor_forecast.py`
- `app/backend/modules/ml/services/budget_forecast.py`
- `app/backend/modules/ml/services/schedule_optimizer.py`
- `app/frontend/src/modules/cheftech/forecast/ForecastDashboard.tsx`
- `app/frontend/src/modules/cheftech/forecast/DowntimeForecastChart.tsx`
- `app/frontend/src/modules/cheftech/forecast/LaborForecastChart.tsx`
- `app/frontend/src/modules/cheftech/forecast/BudgetForecastCard.tsx`
- `app/frontend/src/modules/cheftech/forecast/ScheduleOptimizerPanel.tsx`
- `app/frontend/src/modules/cheftech/forecast/TechnicianScheduleView.tsx`
- `app/frontend/src/modules/shared/dashboard/ForecastSummaryTile.tsx`
- `app/frontend/src/modules/shared/machines/components/MachineForecastPanel.tsx`
- `tests/backend/forecast_downtime.test.py`
- `tests/backend/forecast_labor.test.py`
- `tests/backend/forecast_budget.test.py`
- `tests/backend/forecast_schedule.test.py`
- `app/frontend/src/modules/cheftech/forecast/forecastTransforms.test.ts`

**Modify:**
- `app/backend/modules/ml/router.py` — add 6 endpoints + `_require_planner` guard
- `app/backend/requirements.txt` — add `ortools>=9.7`
- `app/frontend/src/App.tsx` (or router file) — add `/forecast` route
- `app/frontend/src/modules/cheftech/dashboard/components/` — embed `ForecastSummaryTile`
- `app/frontend/src/modules/shared/machines/components/MachineDetailPage.tsx` (or equivalent) — embed `MachineForecastPanel`
