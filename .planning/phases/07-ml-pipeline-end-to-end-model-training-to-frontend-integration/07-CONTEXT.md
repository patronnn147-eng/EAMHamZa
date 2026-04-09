# Phase 07: ML Pipeline End-to-End — Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the full ML pipeline chain: consistent backend predictions across all endpoints, telemetry validation, accurate frontend display of all ML values, telemetry update UX, and a smart retraining workflow with admin feedback.

**NOT in scope:** New ML models, new prediction types, new dashboard pages.
</domain>

<decisions>
## Implementation Decisions

### 1. Prediction Consistency (fleet vs per-machine)

**Root cause identified:** `fleet/dashboard` and `fleet/critical` call `calculate_rul(machine, interventions)` without `open_work_orders` and `recent_interventions`. The per-machine endpoint `/machines/{id}/prediction` passes them. Health scores differ between fleet view and detail panel.

**Fix:**
- Both `fleet/dashboard` and `fleet/critical` must pass `open_work_orders` and `recent_interventions` to `calculate_rul`, identical to the per-machine endpoint
- Batch-fetch strategy to avoid N+1:
  - 1 query: all machines
  - 1 query: all interventions (group by machine_id in Python)
  - 1 query: open work order counts per machine (GROUP BY machine_id, exclude TERMINÉ/ANNULÉ)
  - Then compute `recent_interventions` per machine from the in-memory grouped data
- This applies to BOTH fleet endpoints

### 2. Telemetry Defaults & Validation

**Root cause identified:** `getattr(machine, 'air_temperature', 300.0) or 300.0` silently substitutes fake defaults for NULL sensor fields, making predictions look real when they aren't.

**Fix:**
- If ANY of the 5 telemetry fields (`air_temperature`, `process_temperature`, `rotational_speed`, `torque`, `tool_wear`) is NULL in the DB, skip ML prediction
- Return response with `no_telemetry: true`, `health_score: null`, `reliability_score: null`, `risk_level: "UNKNOWN"`, `rul_days: null`
- This applies in `calculate_rul` before any model call
- Frontend: machines with `no_telemetry: true` render as a grey card with label "Aucun capteur" — no ML metrics shown

### 3. Telemetry Update UX

The `PATCH /api/v1/ml/machines/{id}/telemetry` endpoint exists. Add a telemetry edit form to the ML machine detail panel so users can set sensor values directly from the dashboard. This allows testing predictions with meaningful data.

- Inline form in the detail panel (or a small modal accessible from the detail panel)
- Fields: Air temp (K), Process temp (K), RPM, Torque (Nm), Tool wear (min)
- On save: calls PATCH telemetry, then re-fetches prediction
- Visible only when user has appropriate role (admin or cheftech)

### 4. New Machines (0 interventions)

Machines with 0 interventions get `health_score=100`, `reliability_score=100` (hardcoded). Keep this logic but:
- Add `is_new_machine: true` flag to response when `data_points == 0`
- Frontend: show a badge "Nouvelle machine — données insuffisantes" alongside the 100/100 scores

### 5. Model Retraining Workflow

**Trigger:** Manual (admin button) + threshold notification at 25 new labelled records.

**Implementation:**
- `RetrainingService.get_retraining_stats()` already exists — add a `pending_records` count to the response (interventions with `actual_failure_type` filled that were logged after last retrain)
- When `pending_records >= 25`: ML admin dashboard shows an inline yellow banner at the top of the page:
  `"X nouvelles interventions disponibles pour le réentraînement — Lancer maintenant [button]"`
- The banner disappears after retraining is triggered
- **Do NOT use the notification system** (it's unreliable) — banner is inline in the ML admin page only
- After retraining completes, show a success summary inline: models retrained, data count used, key metric per model

### 6. Frontend Type Accuracy

**Bug:** `failure_type_predictions` in `MLPrediction` and `FleetMachineCard` interfaces is typed as `{TWF?: number, HDF?: number, ...}` (flat probabilities). Backend actually returns `failure_types: {TWF: {detected: bool, probability: float}, ...}`.

**Fix:**
- Update `MLPrediction` and `FleetMachineCard` in `app/frontend/src/lib/types.ts`
- Rename field from `failure_type_predictions` to `failure_types` to match backend
- Type: `{[key: string]: {detected: boolean; probability: number}}`
- Update all components that render this field

### 7. Fake Health History

The `MachineDetailPanel` generates 14 days of random fake health history data as a fallback. 

**Fix:**
- Remove the random health history generation entirely
- If the per-machine `/machines/{id}/prediction` call fails or returns no `health_history`, hide the `HealthTrendChart` component
- Show a placeholder: "Historique non disponible"

</decisions>

<specifics>
## Specific Requirements

### Backend Changes

1. **`ml_predictive.py` — `calculate_rul()`**
   - Add telemetry null check at the top of the function before any model calls
   - If any of 5 telemetry fields is None/NULL: return early with `no_telemetry` response
   - Add `is_new_machine` flag when `len(interventions) == 0`

2. **`router.py` — `get_fleet_dashboard()`**
   - Replace machine-by-machine loop with batch fetch:
     ```
     - fetch all machines (1 query)
     - fetch all interventions grouped by machine_id (1 query)  
     - fetch open work order counts per machine_id (1 query via GROUP BY)
     - compute recent_interventions (last 30 days) from in-memory data
     - pass all params to calculate_rul()
     ```

3. **`router.py` — `get_fleet_critical_predictions()`**
   - Same batch-fetch strategy as fleet/dashboard
   - Pass `open_work_orders` and `recent_interventions` to `calculate_rul()`

4. **`services/ml_retraining.py` — `get_retraining_stats()`**
   - Add `pending_records` to the returned stats dict: count of interventions with `actual_failure_type` set, logged after the last retrain date

### Frontend Changes

5. **`app/frontend/src/lib/types.ts`**
   - Update `MLPrediction` and `FleetMachineCard`:
     - Remove `failure_type_predictions?: {TWF?, ...}`
     - Add `failure_types?: {[key: string]: {detected: boolean; probability: number}}`
     - Add `no_telemetry?: boolean`
     - Add `is_new_machine?: boolean`
   - Update `FleetDashboardResponse` and `FleetCriticalResponse` if needed

6. **Fleet dashboard card component**
   - If `machine.no_telemetry === true`: render grey card variant with "Aucun capteur" label, no ML metrics
   - If `machine.is_new_machine === true`: show "Nouvelle machine — données insuffisantes" badge alongside health scores

7. **`MachineDetailPanel.tsx`**
   - Remove random fake `health_history` generation in the fallback block
   - If no `health_history` in response: don't render `<HealthTrendChart>`, render placeholder instead
   - Fix `failure_types` field rendering to use `{detected, probability}` shape
   - Add telemetry edit form (inline or small modal):
     - Fields: 5 sensor values
     - Submit calls `PATCH /api/v1/ml/machines/{id}/telemetry`
     - On success: re-fetch prediction data
     - Show only for admin/cheftech roles

8. **`MLDashboard.tsx` (admin ML dashboard)**
   - Read `pending_records` from retrain stats
   - When `pending_records >= 25`: render inline yellow banner with "Lancer maintenant" button
   - After retrain: show success summary inline (models, data count, metrics)
   - Do NOT use the notification system

</specifics>

<code_context>
## Key Files

- `app/backend/modules/ml/ml_predictive.py` — MachineLearningService, calculate_rul(), all P1-P6 model loading
- `app/backend/modules/ml/router.py` — All ML API endpoints
- `app/backend/modules/ml/services/ml_retraining.py` — RetrainingService, get_retraining_stats()
- `app/frontend/src/lib/types.ts:148` — MLPrediction, FleetMachineCard, FleetDashboardResponse types
- `app/frontend/src/modules/shared/ml-fleet-dashboard/hooks/useMLFleetData.ts` — Fleet data fetching hook
- `app/frontend/src/modules/shared/ml-fleet-dashboard/components/MachineDetailPanel.tsx` — Machine detail panel with fake history bug at line ~111
- `app/frontend/src/modules/admin/ml/MLDashboard.tsx` — Admin ML dashboard (retrain UI lives here)

## Constraints Carried Forward

- Pure in-memory Python only — no Redis or external services (Phase 03)
- No breaking changes to API contracts (PROJECT.md)
- Docker-based workflow (all Python runs in Docker)
- Notification system is unreliable — use inline UI patterns instead
</code_context>

<deferred>
## Deferred Ideas

- Scheduled auto-retraining (nightly/weekly) — mentioned but kept manual+threshold for now
- Full telemetry data pipeline from real sensors — simulation mode only for now
- ML prediction accuracy tracking / model performance dashboard — separate phase
</deferred>

---

*Phase: 07-ml-pipeline-end-to-end-model-training-to-frontend-integration*
*Context gathered: 2026-04-08*
