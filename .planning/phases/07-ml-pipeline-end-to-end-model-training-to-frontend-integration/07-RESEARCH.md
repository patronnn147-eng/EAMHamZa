# Phase 07: ML Pipeline End-to-End — Research

**Researched:** 2026-04-08
**Domain:** FastAPI ML service + React TypeScript frontend (bug fixes + UX additions)
**Confidence:** HIGH — all findings based on direct source code inspection

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

1. **Prediction Consistency** — Both `fleet/dashboard` and `fleet/critical` must pass `open_work_orders` and `recent_interventions` to `calculate_rul`, using a 3-query batch strategy (all machines / all interventions grouped by machine_id / open work order counts per machine_id).

2. **Telemetry Defaults** — If ANY of the 5 telemetry fields is NULL in DB, skip ML prediction. Return `no_telemetry: true`, `health_score: null`, `reliability_score: null`, `risk_level: "UNKNOWN"`, `rul_days: null`.

3. **Telemetry Update UX** — Add telemetry edit form to `MachineDetailPanel` (inline form or small modal). Fields: 5 sensor values. On save: PATCH `/api/v1/ml/machines/{id}/telemetry`, then re-fetch prediction. Visible to admin/cheftech roles only.

4. **New Machines** — Keep `health_score=100`, `reliability_score=100` for 0-intervention machines, but add `is_new_machine: true` flag in response. Frontend: show "Nouvelle machine — données insuffisantes" badge.

5. **Retraining Workflow** — `get_retraining_stats()` adds `pending_records` count. Banner appears inline in `MLDashboard.tsx` when `pending_records >= 25`. Do NOT use the notification system. Post-retrain shows success summary inline.

6. **Frontend Type Accuracy** — Rename `failure_type_predictions` → `failure_types`, change type to `{[key: string]: {detected: boolean; probability: number}}`. Add `no_telemetry?: boolean` and `is_new_machine?: boolean` to both `MLPrediction` and `FleetMachineCard`.

7. **Fake Health History** — Remove random generation in `MachineDetailPanel` fallback block. If no `health_history` in response, hide `HealthTrendChart`, show "Historique non disponible" placeholder.

### Claude's Discretion

- Inline form vs. small modal for telemetry editing in `MachineDetailPanel`
- Exact visual styling for the no-telemetry grey card variant
- Exact visual styling for the is_new_machine badge

### Deferred Ideas (OUT OF SCOPE)

- Scheduled auto-retraining (nightly/weekly)
- Full telemetry data pipeline from real sensors
- ML prediction accuracy tracking / model performance dashboard
</user_constraints>

---

## Summary

This phase is a targeted bug-fix and UX-completion phase, not new feature development. All 7 changes are surgical: 4 backend modifications and 4 frontend modifications to files that already exist. There are no new libraries to install, no new API routes, and no schema migrations required.

The root causes are well-understood from code inspection. The `calculate_rul()` function in `ml_predictive.py` (lines 102-105) silently substitutes fake telemetry defaults using `or 300.0` / `or 1500`. The fleet endpoints (`router.py` lines 186 and 210) call `calculate_rul(machine, list(interventions))` without `open_work_orders` or `recent_interventions` parameters. The `MachineDetailPanel.tsx` (lines 111-121) generates random fake health history as fallback. The `MLPrediction` and `FleetMachineCard` TypeScript types (lines 164-170) use the wrong shape for failure type data. The `RetrainingService.get_retraining_stats()` returns only `new_data_points` without `pending_records`. The `MLDashboard.tsx` uses `useToast` for retrain results instead of inline state.

The critical constraint is the batch-fetch strategy for fleet endpoints: replace per-machine loops with 3 grouped queries to avoid N+1 at fleet scale.

**Primary recommendation:** Fix in this order — backend telemetry null check first (affects all predictions), then fleet batch-fetch (consistency fix), then retraining stats, then frontend types (prerequisite for component fixes), then component fixes.

---

## Standard Stack

No new libraries needed. All work uses the existing stack.

### Core (already installed)
| Library | Version in Use | Purpose | Notes |
|---------|---------------|---------|-------|
| FastAPI + SQLAlchemy async | existing | Backend API + ORM | `AsyncSession`, `select()`, `func.count()` |
| XGBoost + joblib | existing | ML model inference | Already loaded at module level |
| React + TypeScript | existing | Frontend framework | Strict types via `@/lib/types.ts` |
| shadcn/ui | existing | UI components | `Dialog`, `Badge`, `Button`, `Input`, `Label` available |
| lucide-react | existing | Icons | Already imported in affected components |

### No Installation Required

All dependencies are already present. This phase only modifies existing files.

---

## Architecture Patterns

### Pattern 1: SQLAlchemy Batch-Fetch with In-Memory Grouping

**What:** Replace per-machine loops (N+1 pattern) with 3 upfront queries, then compute per-machine values in Python dicts.

**When to use:** Both `get_fleet_dashboard()` and `get_fleet_critical_predictions()`.

**Current broken pattern (router.py lines 178-190 and 202-214):**
```python
# BROKEN: N+1 — one DB query per machine
for machine in machines:
    interventions_query = select(Ordres_intervention).where(...)
    interventions = (await db.execute(interventions_query)).scalars().all()
    pred = MachineLearningService.calculate_rul(machine, list(interventions))
```

**Fixed pattern:**
```python
# CORRECT: 3 queries total, then in-memory grouping
from sqlalchemy import func
from datetime import datetime, timedelta, timezone

# Query 1: all machines
result = await db.execute(select(Machines))
machines = result.scalars().all()

# Query 2: all interventions for all machines
all_interventions = (await db.execute(select(Ordres_intervention))).scalars().all()

# Query 3: open work order counts per machine
wo_counts_result = await db.execute(
    select(Ordres_travail.machine_id, func.count(Ordres_travail.id).label("cnt"))
    .where(~Ordres_travail.statut.in_(["TERMINÉ", "ANNULÉ"]))
    .group_by(Ordres_travail.machine_id)
)
open_wo_by_machine: dict[int, int] = {row.machine_id: row.cnt for row in wo_counts_result}

# In-memory grouping
from collections import defaultdict
interventions_by_machine: dict[int, list] = defaultdict(list)
for itv in all_interventions:
    if itv.machine_id:
        interventions_by_machine[itv.machine_id].append(itv)

now_dt = datetime.now(timezone.utc)
thirty_days_ago = now_dt - timedelta(days=30)

# Per-machine compute
for machine in machines:
    machine_interventions = interventions_by_machine[machine.id]
    open_wo = open_wo_by_machine.get(machine.id, 0)
    recent_count = sum(
        1 for i in machine_interventions
        if i.date_intervention and (
            i.date_intervention.replace(tzinfo=timezone.utc)
            if i.date_intervention.tzinfo is None
            else i.date_intervention
        ) > thirty_days_ago
    )
    pred = MachineLearningService.calculate_rul(
        machine,
        machine_interventions,
        open_work_orders=open_wo,
        recent_interventions=recent_count
    )
```

### Pattern 2: Telemetry Null Guard in calculate_rul()

**What:** Check all 5 telemetry fields for None BEFORE extracting values with `or` defaults.

**Where:** `ml_predictive.py`, top of `calculate_rul()`, before line 102.

**Important:** The current code uses `getattr(machine, 'air_temperature', 300.0) or 300.0` — this masks both missing attributes AND database NULL values. The `Machines` model shows all telemetry columns are `nullable=True` with `server_default` only, meaning in Python the value is `None` when not set (SQLAlchemy does not apply `server_default` as Python-side defaults).

```python
# Add before Step 1 in calculate_rul():
_telemetry_fields = ['air_temperature', 'process_temperature', 'rotational_speed', 'torque', 'tool_wear']
if any(getattr(machine, f, None) is None for f in _telemetry_fields):
    return {
        "machine_id": machine.id,
        "machine_name": machine.nom,
        "no_telemetry": True,
        "health_score": None,
        "reliability_score": None,
        "risk_level": "UNKNOWN",
        "rul_days": None,
        "failure_probability": None,
        "predicted_failure_date": None,
        "data_points": len(interventions),
        "is_anomaly": False,
        "anomaly_score": 0.0,
        "explanations": [],
    }
```

### Pattern 3: is_new_machine Flag

**What:** Add `is_new_machine: true` to the response dict when `len(interventions) == 0`, AFTER the existing new-machine hardcoding (current line 186 in `calculate_rul`).

**Where:** Inside the `if len(interventions) == 0:` block at Step 7 in `calculate_rul()`.

```python
# Add to response dict construction (after the == 0 hardcoding):
response["is_new_machine"] = len(interventions) == 0
```

### Pattern 4: pending_records in RetrainingService

**What:** Add `pending_records` count to `get_retraining_stats()`.

**Where:** `ml_retraining.py`, `get_retraining_stats()` — currently returns `{"new_data_points": new_points}`.

**Root cause:** The current query already counts interventions with `actual_failure_type != None` and `retrained == False` — this IS the `pending_records` count. The field just needs to be added alongside `new_data_points`.

```python
@staticmethod
async def get_retraining_stats(db: AsyncSession):
    query = select(Ordres_intervention).where(
        Ordres_intervention.actual_failure_type != None,
        Ordres_intervention.retrained == False
    )
    result = await db.execute(query)
    new_points = len(result.scalars().all())
    return {
        "new_data_points": new_points,
        "pending_records": new_points,   # same count, explicit field for frontend threshold check
    }
```

Note: `pending_records` and `new_data_points` refer to the same data (unlabelled-but-feedback-filled interventions). The frontend triggers on `pending_records >= 25`.

### Pattern 5: TypeScript Type Corrections

**What:** Update `MLPrediction`, `FleetMachineCard`, and `DetailedPrediction` (local interface in `MachineDetailPanel.tsx`) to use correct field names and shapes.

**Where:** `app/frontend/src/lib/types.ts` (lines 147-223) and `MachineDetailPanel.tsx` (lines 47-72).

```typescript
// In types.ts — replace failure_type_predictions with:
failure_types?: {
  [key: string]: { detected: boolean; probability: number };
};
no_telemetry?: boolean;
is_new_machine?: boolean;
```

Apply to both `MLPrediction` (line 147) and `FleetMachineCard` (line 173).

**Also update `DetailedPrediction` in `MachineDetailPanel.tsx`** — this is a LOCAL interface (lines 47-72) that duplicates `MLPrediction`. It must be updated identically, or replaced with `import type { MLPrediction }` plus the `health_history` extension.

### Pattern 6: Telemetry Edit Form in MachineDetailPanel

**What:** Add inline edit form guarded by role check. Uses `useAuth` from `AuthContext`.

**Role check pattern** (from `AuthContext.tsx`):
```typescript
import { useAuth } from '@/contexts/AuthContext';
// ...
const { user } = useAuth();
const canEditTelemetry = user?.role === 'admin' || user?.role === 'cheftech';
```

**PATCH telemetry call pattern:**
```typescript
const handleTelemetrySave = async (values: TelemetryFormValues) => {
  const token = localStorage.getItem('access_token');
  const res = await fetch(`/api/v1/ml/machines/${machine.machine_id}/telemetry`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(values),
  });
  if (res.ok) {
    fetchPrediction(); // re-fetch the prediction after telemetry update
  }
};
```

**shadcn/ui components to use:** `Input`, `Label`, `Button` — all already available in the project.

### Pattern 7: No-Telemetry Card Variant in FleetOverview

**What:** In `FleetOverview.tsx`, machines with `no_telemetry === true` render differently — grey card, "Aucun capteur" label, no ML metrics displayed.

**Important:** `FleetMachineCard` does NOT include `no_telemetry` yet (it's being added in the types fix). After types.ts is updated, `FleetOverview.tsx` can use `machine.no_telemetry`.

**Rendering pattern:**
```tsx
// In the machine card rendering loop (FleetOverview.tsx ~line 182)
if (machine.no_telemetry) {
  return (
    <Card key={machine.machine_id} className="border-gray-200 bg-gray-50 opacity-75">
      {/* minimal card: name, zone, "Aucun capteur" badge */}
    </Card>
  );
}
```

### Pattern 8: MLDashboard Inline Retrain Banner

**What:** Replace toast notifications with inline state-driven banner. Add `retrainResult` state to show post-retrain summary inline.

**Where:** `MLDashboard.tsx`

**Current state interface:**
```typescript
interface MLStats {
    new_data_points: number;
    // ADD:
    pending_records: number;
}
```

**Banner rendering pattern:**
```tsx
{stats && stats.pending_records >= 25 && !retraining && !retrainResult && (
  <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 flex items-center justify-between">
    <span className="text-sm text-amber-800">
      {stats.pending_records} nouvelles interventions disponibles pour le réentraînement
    </span>
    <Button size="sm" onClick={handleRetrain} className="bg-amber-500 hover:bg-amber-600 text-white">
      Lancer maintenant
    </Button>
  </div>
)}
```

**Post-retrain success summary** (inline, not toast):
```tsx
{retrainResult && retrainResult.status === 'success' && (
  <div className="rounded-lg border border-green-300 bg-green-50 px-4 py-3">
    <p className="text-sm text-green-800 font-semibold">{retrainResult.message}</p>
    {retrainResult.new_total_samples && (
      <p className="text-xs text-green-700 mt-1">
        Données utilisées: {retrainResult.new_total_samples} échantillons
      </p>
    )}
  </div>
)}
```

Remove the `useToast` import and `toast()` calls from `handleRetrain`.

### Pattern 9: Remove Fake Health History

**What:** Remove lines 111-121 in `MachineDetailPanel.tsx` (the `Array.from({ length: 14 }, ...)` random history generation in the fallback block).

**Replace fallback with:**
```tsx
setPrediction({
  machine_id: machine.machine_id,
  machine_name: machine.machine_name,
  rul_days: machine.rul_days,
  // ... other fields from machine card data
  health_history: undefined,  // explicitly no fake data
});
```

**HealthTrendChart conditional** (already correct at line 268, no change needed):
```tsx
{displayData.health_history && displayData.health_history.length > 0 && (
  <HealthTrendChart data={displayData.health_history} />
)}
```

Add a placeholder below this block:
```tsx
{(!displayData.health_history || displayData.health_history.length === 0) && (
  <div className="p-4 rounded-xl bg-gray-50 border text-center text-sm text-gray-500">
    Historique non disponible
  </div>
)}
```

### Pattern 10: failure_types Rendering in MachineDetailPanel

**What:** The current rendering (lines 242-259) treats `failure_type_predictions` values as raw numbers (multiplies by 100). After type fix, values are `{detected: boolean; probability: number}`.

**Updated rendering:**
```tsx
{displayData.failure_types && (
  <div className="p-4 rounded-xl bg-gray-50 border">
    <div className="flex items-center gap-2 mb-3">
      <FileText className="h-4 w-4 text-gray-500" />
      <span className="text-sm font-bold text-gray-700">Prédictions de Type de Défaillance (P2)</span>
    </div>
    <div className="grid grid-cols-5 gap-2">
      {Object.entries(displayData.failure_types).map(([type, data]) => (
        <div key={type} className={`text-center p-2 rounded-lg border ${data.detected ? 'bg-red-50 border-red-200' : 'bg-white'}`}>
          <p className="text-xs font-bold text-gray-600">{type}</p>
          <p className={`text-lg font-black ${data.detected ? 'text-red-600' : 'text-gray-800'}`}>
            {data.probability.toFixed(0)}%
          </p>
        </div>
      ))}
    </div>
  </div>
)}
```

### Anti-Patterns to Avoid

- **Silent NULL masking:** Do not use `getattr(machine, field, default) or default` anywhere in the updated code — this was the root cause of the telemetry bug.
- **Per-machine DB queries in loops:** Do not replicate the existing N+1 pattern in any new fleet endpoints.
- **Toast for critical feedback:** Do not use `useToast` for retrain outcomes — the decision is inline UI only.
- **Copying the broken `DetailedPrediction` interface:** When fixing types.ts, also fix the local `DetailedPrediction` interface in `MachineDetailPanel.tsx` — it's a copy of the old shape.
- **Forgetting the `failure_types` field is absent from `calculate_rul()` response:** The backend `calculate_rul()` currently does NOT include `failure_types` in its return dict (P2 results are only used internally for MTTR adjustment). The fix must add `failure_types` to the response dict.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Role-gated UI | Custom role check prop drilling | `useAuth()` from `AuthContext.tsx` — already has `user.role` | Hook is already wired up in the app |
| Batch DB aggregation | Python loops | SQLAlchemy `func.count()` + `group_by()` | Already used in `get_machine_prediction()` at line 60 of router.py |
| Telemetry PATCH | New fetch logic | Reuse same fetch pattern already in `MachineDetailPanel.useEffect` | Pattern: `localStorage.getItem('access_token')` + `Bearer` header |
| Form inputs | Custom form component | shadcn/ui `Input` + `Label` | Already used throughout the app |

---

## Common Pitfalls

### Pitfall 1: `failure_types` Not in calculate_rul() Response
**What goes wrong:** Frontend type fix expects `failure_types` from the prediction endpoint, but `calculate_rul()` never adds P2 results to the response dict. Types compile, but the field is always `undefined`.
**Why it happens:** P2 is called inside `calculate_rul()` (line 195) to adjust MTTR, but the `types` variable is local and never put into `response`.
**How to avoid:** Explicitly add to the response dict: `response["failure_types"] = MachineLearningService.predict_failure_type(features_6) if _ml_model_p2 is not None else {}` — but only when `len(interventions) > 0`.
**Warning signs:** `displayData.failure_types` is always undefined in the component, section never renders.

### Pitfall 2: `pending_records` vs `new_data_points` Confusion
**What goes wrong:** Both fields return the same count from the same query — but the frontend threshold check uses `pending_records` and the existing "Nouveaux points" card uses `new_data_points`. If only one is added, the other breaks.
**Why it happens:** The current `get_retraining_stats()` only returns `new_data_points`. The `MLStats` interface needs BOTH.
**How to avoid:** Return both keys from `get_retraining_stats()` and update `MLStats` interface to add `pending_records`.

### Pitfall 3: `UNKNOWN` risk_level Breaking Frontend Sorting/Filtering
**What goes wrong:** `FleetOverview.tsx` sorts using `riskConfig[machine.risk_level]?.order ?? 3`. If `risk_level === "UNKNOWN"`, `riskConfig["UNKNOWN"]` is `undefined`, defaults to order 3 (same as LOW). No crash, but no-telemetry machines sort alongside LOW machines.
**Why it happens:** `riskConfig` in `FleetOverview.tsx` only has CRITICAL/HIGH/MEDIUM/LOW keys.
**How to avoid:** No-telemetry machines are rendered as a separate grey card variant BEFORE the normal rendering logic — they never reach the `riskConfig` sort lookup. Use early return in the card rendering loop.

### Pitfall 4: `health_score: null` Breaking FleetOverview Math
**What goes wrong:** `FleetOverview` computes `avgHealthScore` as `machines.reduce((sum, m) => sum + (m.health_score || 0), 0) / machines.length`. With `health_score: null`, the `|| 0` fallback means null machines count as 0, lowering the average artificially.
**Why it happens:** `useMLFleetData.ts` (line 57) reduces over all machines including null-health ones.
**How to avoid:** Filter out no-telemetry machines from the average calculation: `machines.filter(m => !m.no_telemetry)`.

### Pitfall 5: `DetailedPrediction` Local Interface Not Updated
**What goes wrong:** `MachineDetailPanel.tsx` defines a LOCAL `DetailedPrediction` interface (lines 47-72) with `failure_type_predictions` (old wrong type). Updating `types.ts` alone doesn't fix the component — the local interface still uses the old shape.
**Why it happens:** The component developer copied the type instead of importing it.
**How to avoid:** Either update the local `DetailedPrediction` interface identically to `MLPrediction`, or replace it with a `Pick<MLPrediction, ...> & { health_history?: ... }` extension.

### Pitfall 6: Telemetry Form Triggering Re-fetch Before DB Commit
**What goes wrong:** If `fetchPrediction()` is called immediately in the `then` callback of the PATCH, the new prediction fetch may race with DB commit on the backend.
**Why it happens:** `router.py`'s `update_machine_telemetry` calls `await db.commit()` then `await db.refresh(machine)` before returning — so by the time the PATCH 200 response arrives, the DB is committed. No race issue in practice.
**How to avoid:** Call `fetchPrediction()` after checking `res.ok` (not in a race). Already safe.

### Pitfall 7: `no_telemetry` Response Missing Required Fleet Fields
**What goes wrong:** `FleetOverview.tsx` accesses `machine.machine_id`, `machine.machine_name`, `machine.zone`, `machine.sous_zone`, `machine.statut` directly without null checks. The no-telemetry response from `calculate_rul()` must include these fields.
**Why it happens:** The early-return dict in `calculate_rul()` only has ML fields.
**How to avoid:** Always include `machine_id`, `machine_name` in the no-telemetry early return. In fleet endpoints, add `zone`, `sous_zone`, `statut` to the response just as the current code does (lines 211-213 of router.py).

---

## Code Examples

### Fleet Endpoint: Correct Batch Telemetry State for both fleet endpoints

```python
# Source: Direct code inspection of router.py and ml_predictive.py
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from sqlalchemy import func

# At top of get_fleet_dashboard() and get_fleet_critical_predictions():
result = await db.execute(select(Machines))
machines = result.scalars().all()

all_itv_result = await db.execute(select(Ordres_intervention))
all_interventions = all_itv_result.scalars().all()

wo_result = await db.execute(
    select(Ordres_travail.machine_id, func.count(Ordres_travail.id).label("cnt"))
    .where(~Ordres_travail.statut.in_(["TERMINÉ", "ANNULÉ"]))
    .group_by(Ordres_travail.machine_id)
)
open_wo_by_machine = {row.machine_id: row.cnt for row in wo_result}

interventions_by_machine = defaultdict(list)
for itv in all_interventions:
    if itv.machine_id:
        interventions_by_machine[itv.machine_id].append(itv)

now_dt = datetime.now(timezone.utc)
thirty_days_ago = now_dt - timedelta(days=30)
```

### Backend: Telemetry Null Guard

```python
# Source: Direct inspection of ml_predictive.py calculate_rul()
# Add at the very top of calculate_rul(), before Step 1:
_TELEMETRY_FIELDS = ('air_temperature', 'process_temperature', 'rotational_speed', 'torque', 'tool_wear')
if any(getattr(machine, f, None) is None for f in _TELEMETRY_FIELDS):
    return {
        "machine_id": machine.id,
        "machine_name": machine.nom,
        "no_telemetry": True,
        "health_score": None,
        "reliability_score": None,
        "risk_level": "UNKNOWN",
        "rul_days": None,
        "failure_probability": None,
        "predicted_failure_date": None,
        "data_points": len(interventions),
        "is_anomaly": False,
        "anomaly_score": 0.0,
        "explanations": [],
        "failure_types": {},
    }
```

### Backend: failure_types in Response

```python
# Add to the response dict construction inside calculate_rul()
# Only when len(interventions) > 0 (already inside that branch):
failure_types = {}
if _ml_model_p2 is not None:
    failure_types = MachineLearningService.predict_failure_type(features_6)

response = {
    # ... existing fields ...
    "failure_types": failure_types,
    "is_new_machine": len(interventions) == 0,
}
```

### Frontend: Role-Gated Telemetry Form

```typescript
// Source: AuthContext.tsx inspection — user.role is a string
import { useAuth } from '@/contexts/AuthContext';

const { user } = useAuth();
const canEditTelemetry = user?.role === 'admin' || user?.role === 'cheftech';
```

---

## State of the Art

| Old Approach | Current Approach | Impact for This Phase |
|--------------|------------------|-----------------------|
| Per-machine DB query in loop | Batch query + in-memory grouping | Fleet endpoints must use batch pattern |
| `getattr(m, f, default) or default` | Explicit null check before extraction | Must change to guard, not mask |
| Toast notifications for retrain | Inline banner + inline summary | Do not introduce toast back |

---

## Open Questions

1. **`failure_types` in `FleetMachineCard`**
   - What we know: Fleet endpoints return data from `calculate_rul()` response. Once `failure_types` is added to the `calculate_rul()` response dict, it will naturally appear in fleet endpoint responses.
   - What's unclear: Whether `FleetOverview.tsx` should render failure type data in the card list view (it currently doesn't). The CONTEXT.md only mentions fixing the type shape, not displaying it in fleet cards.
   - Recommendation: Only fix the type shape in `FleetMachineCard`. Do not add rendering of failure types to fleet overview cards (scope creep risk).

2. **Role string values for `cheftech`**
   - What we know: `AuthContext.tsx` stores `user.role` as a string. `isAdmin` is computed in the context. The role values used in routing and guards elsewhere in the codebase need verification.
   - What's unclear: Is the role string exactly `"cheftech"` or `"CHEFTECH"` or something else?
   - Recommendation: Before implementing the role guard, grep for `user.role` usage in the codebase to confirm the exact string value.

3. **Cache invalidation after telemetry PATCH**
   - What we know: Phase 03 added a TTL cache for ML predictions. If predictions are cached, a telemetry PATCH followed by prediction re-fetch may return the old cached value for up to 5 minutes.
   - What's unclear: Whether the cache key includes telemetry values or just machine_id.
   - Recommendation: Check the cache implementation — if keyed by machine_id only, the telemetry edit form should invalidate the cache entry before re-fetching. If TTL is short (5 min), acceptable for simulation use.

---

## Sources

### Primary (HIGH confidence)
- Direct source code inspection of `app/backend/modules/ml/ml_predictive.py` — `calculate_rul()`, all P-model loading, current telemetry extraction pattern
- Direct source code inspection of `app/backend/modules/ml/router.py` — fleet endpoints, per-machine N+1 pattern confirmed at lines 178-190 and 202-214
- Direct source code inspection of `app/backend/modules/ml/services/ml_retraining.py` — `get_retraining_stats()` current return value confirmed
- Direct source code inspection of `app/frontend/src/lib/types.ts` — `MLPrediction` (line 147), `FleetMachineCard` (line 173), wrong `failure_type_predictions` shape confirmed
- Direct source code inspection of `app/frontend/src/modules/shared/ml-fleet-dashboard/components/MachineDetailPanel.tsx` — fake history generation confirmed at lines 111-121, local `DetailedPrediction` interface confirmed
- Direct source code inspection of `app/frontend/src/modules/admin/ml/MLDashboard.tsx` — `useToast` usage, missing `pending_records` in `MLStats` interface
- Direct source code inspection of `app/backend/models/machines.py` — all telemetry columns are `nullable=True`
- Direct source code inspection of `app/frontend/src/contexts/AuthContext.tsx` — `user.role` string, `useAuth` hook pattern

### Secondary (MEDIUM confidence)
- `.planning/phases/07-ml-pipeline-end-to-end-model-training-to-frontend-integration/07-CONTEXT.md` — all locked decisions and root causes documented by the user

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries, all existing code inspected
- Architecture patterns: HIGH — all patterns derived from direct source inspection, exact line numbers cited
- Pitfalls: HIGH — all pitfalls identified from actual code state, not speculation

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (stable codebase, changes only within this phase)
