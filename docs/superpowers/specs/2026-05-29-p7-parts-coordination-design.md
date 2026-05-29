# P7 — Predictive Parts Coordination System

**Date:** 2026-05-29
**Status:** Approved design → implementation
**Scope:** Build all 6 phases (P7.1–P7.6). First of program P7–P10.

---

## Plain-language summary (for non-technical review)

Today the platform warns you *"machine X will likely fail in ~N days"* and *"this is the kind of failure."* It does **not** tell you which spare parts you'll need, how many, or whether the warehouse has them.

P7 adds that — and wires it into the people and paperwork you already have:

1. **The brain** — predicts the parts shopping list per machine for the next 30 days (which parts, how many, are we short, order how many).
2. **Smart alerts** — if you're short a part, the right person gets an alert.
3. **Right view per person** — Admin sees "approve this purchase," chief tech sees "schedule this," technician sees "prep these parts." Plain words. Plus a "why / what if I ignore it / who acts" pop-up.
4. **Auto-paperwork (you approve)** — the system pre-fills the purchase request and work order; a human always says yes/no. Nothing is ordered silently.
5. **Readiness score + timeline** — one simple "how ready are we?" score, and a timeline: predicted → parts reserved → job scheduled → done.
6. **Learning loop** — after each real repair it compares what it predicted vs what was actually used, and improves.

**Most of this reuses machinery that already exists** (roles, alerts, work-orders, approvals, feedback). The genuinely new parts are: the prediction brain, the parts-shortage alert, the per-person screens, the readiness score, and the timeline.

---

## Context

`demand_forecast.py` already aggregates historical stock out-movements into a crude monthly demand number, exposed at `/api/v1/ml/inventory/demand-forecast`. It ignores machine condition (RUL, failure type) and uses no trained model. A prediction without an operational workflow has low business value. P7 turns this into a condition-aware, role-aware coordination system, reusing existing alert/work-order/approval/feedback infrastructure.

## Non-goals (YAGNI)
- No new workflow-builder/configurable state machine.
- No SLA engine, no escalation rules engine (binary approve/reject stays).
- No silent automation — drafts only, human approval mandatory.
- No new prediction/timeline/action tables in v1 (reuse + derive).
- P8–P10 (energy/cost, quality/scrap, failure cascade) are out of scope; separate specs later.

---

## Architecture overview

```
Telemetry → P2 (failure type) + P3 (RUL)  ──┐
                                            ▼
                           P7 engine (predict_parts_demand)
                                            │  parts_demand {items[], source}
              ┌─────────────────────────────┼───────────────────────────┐
              ▼                              ▼                           ▼
   ml_prediction_log               unified-health response        PARTS_SHORTAGE alert
   (+p7_parts_demand JSON)         (parts_demand block)           (alertes.py, routed by role)
              │                              │                           │
              ▼                              ▼                           ▼
      feedback/retrain            role-based UI cards          draft procurement + WO
      (consumed_pieces compare)   + explainability drawer      (human approves → reserve)
              │                              │                           │
              └──────────────► Maintenance Readiness Score + Timeline ◄──┘
```

Reuse-first. New code is thin glue + one model + presentation.

---

## Phase P7.1 — ML engine (the brain)

**Model artifact:** `ml_model_p7_parts_demand.pkl` in BOTH `app/backend/modules/ml/models/` and `app/ml-microservice/models/` (sync rule). Contents:
- `failure_part_map`: `{failure_type: {piece_id: {p_used, expected_qty}}}` — learned from `consumed_pieces` ⋈ `ordres_intervention.actual_failure_type`.
- `consumable_params`: per-piece Croston/SBA params (`is_consumable=True` pieces) from `mouvement_stock` out-movements.
- `meta`: training date, coverage stats, horizon default.

**Research notebook:** `app/ml-microservice/ml_research/p7_parts_demand.ipynb`. Trains from `db_ml_training/` CSVs (`consumed_pieces.csv`, `ordres_intervention.csv`, `mouvement_stock.csv`, `piece_machine.csv`). Saves pkl. Follows P3/P4 notebook conventions (ROOT = `../..`).

**Loader:** add `load_p7()` to model loader (lru_cache, P6 pattern). Add to `startup_check`. *Confirm exact path at impl:* `app/ml-microservice/src/core/model_loader.py` (CLAUDE.md lists `src/model_loader.py` — verify).

**Inference:** `predict_parts_demand(machine_id, rul_days, failure_type_probs, horizon_days=30)` in `predictions.py`:
1. Survival path: for each failure_type with prob > θ (default 0.15), weight = `failure_type_prob × P(fail ≤ horizon | rul_days)` using exponential/Weibull CDF (scale = rul_days). Multiply by `failure_part_map` expected_qty → expected demand per piece.
2. Consumable path: for `is_consumable` pieces not covered by survival path, forecast over horizon from `consumable_params` (Croston/SBA).
3. Merge per piece. Join `stock.quantity`, `pieces.min_stock`. Compute `shortfall = max(0, expected_qty − on_hand)`, `recommended_order_qty = max(shortfall, min_stock − on_hand)`. Reuse `urgency_score` logic from `demand_forecast.py:35-56`. Tag `driver` ("RUL+TWF" or "consumption").
4. If pkl missing → deterministic fallback (current behavior), `source="deterministic_fallback"`.

**Service/router wiring:**
- ml-microservice: new `/predict/parts-demand`; include `parts_demand` in `predict-all` + batch.
- backend: `demand_forecast.py` calls P7; `app/backend/modules/ml/router.py` unified-health adds `parts_demand` block beside `parts_readiness`.

**Output contract:**
```json
"parts_demand": {
  "horizon_days": 30,
  "source": "p7_model | deterministic_fallback",
  "items": [{
    "piece_id": 0, "reference": "", "name": "",
    "expected_qty": 0.0, "on_hand": 0.0, "min_stock": 0,
    "shortfall": 0.0, "urgency_score": 0.0,
    "recommended_order_qty": 0.0, "driver": ""
  }]
}
```

**Frontend:** new "Parts Demand" card in `MLIntelligenceTab.tsx` (glass + Space Grotesk mono, PartsReadinessCard:164-230 pattern). Top-N by urgency: reference/name, expected qty, on-hand vs need, order recommendation. Business name only — never "P7".

**Graduate gate:** map coverage ≥ 5 interventions per failure_type (report, don't hard-block); backtest hold out last 3 months of `consumed_pieces` → P7 demand MAE < deterministic baseline AND < naive (last-period). Graduate only if it beats baseline; else stay on deterministic fallback.

---

## Phase P7.2 — Alert routing

- Add alert type `PARTS_SHORTAGE` to `alertes.py` type set (extensible string + enum). Severity from urgency (CRITICAL if `shortfall>0` on a machine with RUL < horizon; else MEDIUM/HIGH).
- When P7 produces shortfall above threshold (reuse alert config thresholds), create an `alertes` row, link `machine_id` and, if present, `work_order_id`.
- Routing by role via existing `AlertsPanel.tsx` + `ChefTechAlertWorkflow.tsx`. Admin/CHEFTECH see procurement-relevant; TECHNICIEN sees prep-relevant. Dedup: one open PARTS_SHORTAGE alert per (machine, piece) until dismissed/resolved.

---

## Phase P7.3 — Role-based UX + plain language + explainability

Per-role presentation of the same `parts_demand` data (reuse role guards + per-role dashboards):
- **ADMIN:** procurement queue widget + business-risk wording + "Approve procurement" (reuse approval flow).
- **CHEFTECH:** planning recommendation; "Convert to intervention/work order" (reuse creation endpoints).
- **CHETOP:** business-risk framing of machine readiness.
- **TECHNICIEN:** preparation checklist ("prepare these parts / inspect X").

**Plain-language rule:** UI strings must avoid ML jargon (no "Weibull", "Croston", "probability distribution", "feature importance"). Use "risk increasing", "parts likely needed soon", "stock may be insufficient", "recommended preparation".

**Explainability drawer** (shared component) answers: *Why predicted?* (RUL + failure type in plain words) · *What if ignored?* (downtime/rush-order risk) · *What to prepare?* (parts list) · *Who acts?* (role + action).

---

## Phase P7.4 — Auto-draft workflow (guarded)

On shortfall, system creates DRAFT artifacts linked to the originating `ml_prediction_log` row:
- Draft procurement recommendation (parts + recommended_order_qty).
- Draft work order / intervention (status `DRAFT` / `PENDING_APPROVAL`).
- Proposed reservation (not committed until approved).

Human validates via existing admin validate path (`InventoryReservationService.try_reserve()` runs on approval). Reject → discard draft + release. **No silent creation or ordering.**

---

## Phase P7.5 — Readiness score + timeline + KPIs

- **Maintenance Readiness Score** (0–100, on-demand): blend of machine condition (unified_health_score), inventory availability (shortfall coverage), technician readiness (availability/shift), procurement risk (open shortages). Documented equal-ish weights, tunable. New KPI tile on dashboards.
- **Timeline** (derived, no new table): chronological chain per machine from existing timestamps — prediction (`ml_prediction_log.created_at`) → parts reserved (`mouvement_stock` RESERVED) → intervention approved (`ordres_intervention.approved_at`) → WO status transitions → completion. Fills the missing activity-feed gap.
- **KPIs** (computed from existing data): prevented downtime (proxy), avoided rush orders, stock readiness rate, prediction adoption rate (drafts accepted/total).

---

## Phase P7.6 — Feedback closure

- Persist each P7 prediction into `ml_prediction_log` via new `p7_parts_demand` JSON column (mirror existing `p2_failure_types` JSON pattern). DB migration (Alembic) adds the column.
- On intervention completion, compare predicted parts vs actual `consumed_pieces` (qty_used). Record match/error.
- Extend `ml_retraining.py` to queue P7 feedback (reuse `retrained` flag pattern); notebook re-trains map + Croston params from accumulated history.

---

## Implementation notes / reuse references
- Roles & guards: `app/backend/dependencies/auth.py:82` `require_role`; FE `ProtectedRoute`, `RoleBasedRedirect`.
- Reservation: `app/backend/modules/admin/admin_itv.py:102-160`, `InventoryReservationService.try_reserve()`.
- Urgency logic to reuse: `app/backend/modules/ml/services/demand_forecast.py:35-56`.
- Card pattern: `app/frontend/src/modules/shared/machines/components/MLIntelligenceTab.tsx` (PartsReadinessCard:164-230).
- Model sync: pkl in both model dirs; v2 priority + automatic fallback.

## Verification (per-phase gates + E2E)
- **P7.1:** notebook backtest MAE < deterministic; pytest `predict_parts_demand` fixture (known RUL+failure_type → expected parts present, shortfall math correct); unified-health returns `parts_demand`.
- **P7.2:** induced shortfall → `PARTS_SHORTAGE` alert in AlertsPanel for correct role.
- **P7.3:** each role renders correct wording/actions; explainability drawer shows why/what-if/who-acts; grep UI for banned jargon strings = none.
- **P7.4:** shortfall → draft procurement + WO created, linked to prediction, blocked until human approve.
- **P7.5:** Readiness Score tile renders; timeline shows full chain for one machine.
- **P7.6:** completed intervention w/ consumed_pieces → comparison logged → retraining queue picks it up.
- **E2E:** `make up`; walk one machine prediction → alert → approve → WO → complete → feedback across all 4 roles.

## Open items to confirm at implementation
1. Exact `model_loader.py` path (`src/` vs `src/core/`).
2. RUL→failure CDF: exponential vs Weibull (start exponential, scale=rul_days; revisit if backtest weak).
3. θ (failure-type inclusion threshold) and alert severity cutoffs — start 0.15 / tune from data.
4. Readiness Score weights — start equal, calibrate.
