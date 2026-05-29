# P7 Predictive Parts Coordination — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the deterministic spare-parts demand forecast into a condition-aware, role-aware coordination system (predict parts → alert → role UX → guarded auto-draft → readiness/timeline → feedback).

**Architecture:** Reuse-first. One new model (P7) feeds a `parts_demand` contract into `ml_prediction_log`, the unified-health response, a `PARTS_SHORTAGE` alert, role-specific cards, and guarded draft procurement/work-orders. Readiness score + timeline are derived from existing data. Feedback compares predicted vs actual `consumed_pieces`.

**Tech Stack:** Python (Flask ml-microservice, FastAPI backend, SQLAlchemy, Alembic), sklearn/XGBoost + Croston/SBA, Jupyter, Next.js/TypeScript/React frontend, pytest.

**Spec:** `docs/superpowers/specs/2026-05-29-p7-parts-coordination-design.md` — executing subagents MUST read it.

**Token-prudence note (intentional):** P7.1 below is fully code-detailed (foundation + novel math). Phases P7.2–P7.6 are complete task breakdowns (exact files, function signatures, test names, verification gates); the executing subagent for each task authors implementation code from the spec + existing patterns rather than this plan re-inlining large boilerplate. This is a deliberate decision to respect the token budget for a 6-phase build, NOT a set of placeholders. Each task still has a test-first gate and exact paths.

**Global conventions:**
- TDD: failing test → run (fail) → minimal impl → run (pass) → commit. One logical change per commit.
- Models pkl: write to BOTH `app/backend/modules/ml/models/` AND `app/ml-microservice/models/` (sync rule).
- Never surface "P7"/"P1..P6" in UI — business names only.
- UI strings: no ML jargon (no "Weibull/Croston/probability distribution/feature importance").
- Confirm `model_loader.py` exact path at first use (`app/ml-microservice/src/core/model_loader.py` per exploration; CLAUDE.md says `src/model_loader.py`).

---

## File structure (decomposition)

**New:**
- `app/ml-microservice/ml_research/p7_parts_demand.ipynb` — research/training notebook.
- `app/ml-microservice/src/p7_parts_demand.py` — pure forecasting functions (testable, no Flask). Single responsibility: math.
- `app/backend/modules/ml/models/ml_model_p7_parts_demand.pkl` + `app/ml-microservice/models/…` — artifact.
- `app/backend/.../alembic` migration — add `p7_parts_demand` JSON column to `ml_prediction_log`.
- `app/backend/modules/ml/services/readiness.py` — readiness score + timeline derivation.
- Frontend: `PartsDemandCard.tsx`, `ExplainabilityDrawer.tsx`, `ReadinessScoreTile.tsx`, `MaintenanceTimeline.tsx`, role widgets.
- Tests: `app/ml-microservice/tests/test_p7_parts_demand.py`, `app/backend/tests/test_p7_*`.

**Modify (thin glue):**
- `model_loader.py` (+`load_p7`, startup_check), `predictions.py` (+`predict_parts_demand`), ml-microservice `router.py` (+`/predict/parts-demand`, predict-all/batch).
- `app/backend/modules/ml/services/demand_forecast.py` (call P7), `app/backend/modules/ml/router.py` (unified-health `parts_demand` block).
- `app/backend/models/alertes.py` (+`PARTS_SHORTAGE`), `ml_retraining.py` (P7 feedback queue), `MLIntelligenceTab.tsx` (mount card).

---

# PHASE P7.1 — ML engine (foundation, fully detailed)

Pure-function-first so the math is unit-tested without Flask/DB. Survival path + consumable path live in `app/ml-microservice/src/p7_parts_demand.py`.

### Task 1: Survival probability helper

**Files:**
- Create: `app/ml-microservice/src/p7_parts_demand.py`
- Test: `app/ml-microservice/tests/test_p7_parts_demand.py`

- [ ] **Step 1: Write the failing test**

```python
# app/ml-microservice/tests/test_p7_parts_demand.py
import math
from src.p7_parts_demand import p_fail_within

def test_p_fail_within_half_life():
    # exponential: at t == scale, CDF = 1 - e^-1 ≈ 0.632
    assert math.isclose(p_fail_within(horizon=30, rul_days=30), 1 - math.e**-1, rel_tol=1e-6)

def test_p_fail_within_zero_rul_is_certain():
    assert p_fail_within(horizon=30, rul_days=0) == 1.0

def test_p_fail_within_huge_rul_is_small():
    assert p_fail_within(horizon=1, rul_days=10_000) < 0.001
```

- [ ] **Step 2: Run test, verify fail**

Run: `pytest app/ml-microservice/tests/test_p7_parts_demand.py -v`
Expected: FAIL (ImportError / no `p_fail_within`).

- [ ] **Step 3: Minimal implementation**

```python
# app/ml-microservice/src/p7_parts_demand.py
import math

def p_fail_within(horizon: float, rul_days: float) -> float:
    """P(failure within `horizon` days) given remaining useful life estimate.
    Exponential model, scale = rul_days. rul_days<=0 → certain failure."""
    if rul_days <= 0:
        return 1.0
    return 1.0 - math.exp(-horizon / rul_days)
```

- [ ] **Step 4: Run test, verify pass**

Run: `pytest app/ml-microservice/tests/test_p7_parts_demand.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add app/ml-microservice/src/p7_parts_demand.py app/ml-microservice/tests/test_p7_parts_demand.py
git commit -m "feat(p7): add failure-within-horizon probability helper"
```

### Task 2: Survival-path expected demand

**Files:**
- Modify: `app/ml-microservice/src/p7_parts_demand.py`
- Test: `app/ml-microservice/tests/test_p7_parts_demand.py`

- [ ] **Step 1: Write the failing test**

```python
from src.p7_parts_demand import survival_demand

def test_survival_demand_weights_by_prob_and_qty():
    # failure_part_map: failure_type -> {piece_id: {p_used, expected_qty}}
    fmap = {"TWF": {7: {"p_used": 1.0, "expected_qty": 2.0}}}
    ft_probs = {"TWF": 1.0}
    out = survival_demand(ft_probs, rul_days=30, horizon=30, failure_part_map=fmap, theta=0.15)
    # weight = ft_prob(1.0) * p_fail_within(30,30)≈0.632 ; demand = 0.632 * p_used(1) * qty(2)
    assert abs(out[7] - (1 - 2.718281828**-1) * 2.0) < 1e-3

def test_survival_demand_skips_below_theta():
    fmap = {"TWF": {7: {"p_used": 1.0, "expected_qty": 2.0}}}
    assert survival_demand({"TWF": 0.1}, 30, 30, fmap, theta=0.15) == {}
```

- [ ] **Step 2: Run, verify fail.** `pytest …test_p7_parts_demand.py -v` → FAIL (no `survival_demand`).

- [ ] **Step 3: Implementation**

```python
def survival_demand(failure_type_probs: dict, rul_days: float, horizon: float,
                    failure_part_map: dict, theta: float = 0.15) -> dict:
    """Expected demand per piece_id from condition signals.
    demand = Σ_ft [ ft_prob * P(fail<=horizon) * p_used * expected_qty ]."""
    demand: dict = {}
    pf = p_fail_within(horizon, rul_days)
    for ft, prob in failure_type_probs.items():
        if prob < theta:
            continue
        for piece_id, stats in failure_part_map.get(ft, {}).items():
            contrib = prob * pf * stats.get("p_used", 0.0) * stats.get("expected_qty", 0.0)
            demand[piece_id] = demand.get(piece_id, 0.0) + contrib
    return demand
```

- [ ] **Step 4: Run, verify pass.** Expected: PASS.
- [ ] **Step 5: Commit.** `git commit -m "feat(p7): survival-path expected parts demand"`

### Task 3: Croston/SBA consumable forecast

**Files:** modify `p7_parts_demand.py`; test same file.

- [ ] **Step 1: Failing test**

```python
from src.p7_parts_demand import croston_forecast

def test_croston_constant_demand_recovers_rate():
    # steady 2 units every period → per-period ≈ 2
    series = [2, 2, 2, 2, 2]
    rate = croston_forecast(series, alpha=0.4)
    assert abs(rate - 2.0) < 0.3

def test_croston_intermittent_positive_rate():
    series = [0, 0, 5, 0, 0, 5, 0]
    rate = croston_forecast(series, alpha=0.4)
    assert 0 < rate < 5
```

- [ ] **Step 2: Run, verify fail.**
- [ ] **Step 3: Implementation**

```python
def croston_forecast(series: list, alpha: float = 0.4) -> float:
    """Croston intermittent-demand per-period forecast.
    Returns expected units per period (size / interval)."""
    if not series or all(v == 0 for v in series):
        return 0.0
    z = None  # smoothed nonzero size
    x = None  # smoothed interval
    gap = 1
    for v in series:
        if v != 0:
            z = v if z is None else alpha * v + (1 - alpha) * z
            x = gap if x is None else alpha * gap + (1 - alpha) * x
            gap = 1
        else:
            gap += 1
    if not z or not x:
        return 0.0
    return z / x
```

- [ ] **Step 4: Run, verify pass.**
- [ ] **Step 5: Commit.** `git commit -m "feat(p7): Croston intermittent-demand forecast for consumables"`

### Task 4: Merge + shortfall + order qty (the public contract builder)

**Files:** modify `p7_parts_demand.py`; test same file.

- [ ] **Step 1: Failing test**

```python
from src.p7_parts_demand import build_parts_demand

def test_build_parts_demand_shortfall_and_order():
    survival = {7: 2.0}; consumable = {}
    stock = {7: {"reference": "BRG-7", "name": "Bearing", "on_hand": 1.0,
                 "min_stock": 2, "is_consumable": False}}
    out = build_parts_demand(survival, consumable, stock, horizon=30, source="p7_model")
    item = out["items"][0]
    assert out["horizon_days"] == 30 and out["source"] == "p7_model"
    assert item["piece_id"] == 7 and item["expected_qty"] == 2.0
    assert item["shortfall"] == 1.0                      # 2 needed - 1 on hand
    assert item["recommended_order_qty"] == 1.0          # max(shortfall, min_stock-on_hand)=max(1,1)
    assert item["driver"] == "condition"

def test_build_parts_demand_consumable_driver():
    out = build_parts_demand({}, {9: 3.0},
        {9: {"reference": "OIL", "name": "Oil", "on_hand": 10, "min_stock": 5, "is_consumable": True}},
        30, "p7_model")
    assert out["items"][0]["driver"] == "consumption"
    assert out["items"][0]["shortfall"] == 0.0
```

- [ ] **Step 2: Run, verify fail.**
- [ ] **Step 3: Implementation**

```python
def build_parts_demand(survival: dict, consumable: dict, stock: dict,
                       horizon: int, source: str) -> dict:
    """Merge survival + consumable demand, join stock, compute shortfall/order/urgency.
    `stock`: piece_id -> {reference,name,on_hand,min_stock,is_consumable}."""
    items = []
    for pid in set(survival) | set(consumable):
        meta = stock.get(pid, {})
        expected = survival.get(pid, 0.0) + consumable.get(pid, 0.0)
        on_hand = float(meta.get("on_hand", 0.0))
        min_stock = float(meta.get("min_stock", 0) or 0)
        shortfall = max(0.0, expected - on_hand)
        order = max(shortfall, min_stock - on_hand, 0.0)
        driver = "condition" if pid in survival and survival[pid] > 0 else "consumption"
        urgency = round(min(1.0, (shortfall / expected) if expected else 0.0), 4)
        items.append({
            "piece_id": pid, "reference": meta.get("reference", ""),
            "name": meta.get("name", ""), "expected_qty": round(expected, 3),
            "on_hand": on_hand, "min_stock": int(min_stock), "shortfall": round(shortfall, 3),
            "urgency_score": urgency, "recommended_order_qty": round(order, 3), "driver": driver,
        })
    items.sort(key=lambda i: (-i["urgency_score"], -i["shortfall"]))
    return {"horizon_days": horizon, "source": source, "items": items}
```

> Note: at backend integration (Task 8) the `urgency_score` may be replaced by the richer reused logic from `demand_forecast.py:35-56`; keep this simple version for the pure-function contract.

- [ ] **Step 4: Run, verify pass.**
- [ ] **Step 5: Commit.** `git commit -m "feat(p7): merge demand → parts_demand contract with shortfall/order"`

### Task 5: Training notebook → pkl

**Files:** Create `app/ml-microservice/ml_research/p7_parts_demand.ipynb`. Output pkl to both model dirs.

- [ ] **Step 1:** Build notebook cells (follow P3/P4 conventions, ROOT=`../..`):
  1. Load `db_ml_training/{consumed_pieces,ordres_intervention,mouvement_stock,piece_machine,pieces}.csv`.
  2. Build `failure_part_map`: join consumed_pieces→ordres_intervention on intervention_id; group by `actual_failure_type`,`piece_id`; `p_used` = interventions-using / interventions-of-that-failure-type; `expected_qty` = mean `quantity_used` when used.
  3. Build `consumable_params`: for `is_consumable` pieces, monthly out-series from `mouvement_stock` (movement_type='out'); store series (Croston computed at inference) or fitted z/x.
  4. `meta`: train date, per-failure-type coverage counts, default horizon=30, theta=0.15.
  5. Save `ml_model_p7_parts_demand.pkl` (joblib) to both dirs.
- [ ] **Step 2: Backtest cell (graduate gate):** hold out last 3 months of consumed_pieces; predict via `build_parts_demand`; compute MAE vs actual; compare to deterministic baseline + naive (last-period). Print table + coverage. Graduate only if P7 MAE < both.
- [ ] **Step 3: Run notebook** (`docker compose -f docker-compose.notebooks.yml up --build`, http://localhost:8888). Verify pkl written to both dirs.
- [ ] **Step 4: Commit** pkl + notebook.

```bash
git add app/ml-microservice/ml_research/p7_parts_demand.ipynb \
        app/ml-microservice/models/ml_model_p7_parts_demand.pkl \
        app/backend/modules/ml/models/ml_model_p7_parts_demand.pkl
git commit -m "feat(p7): training notebook + parts-demand model artifact"
```

### Task 6: Loader `load_p7`

**Files:** Modify model_loader (confirm path). Test: `app/ml-microservice/tests/test_loader_p7.py`.

- [ ] **Step 1: Failing test**

```python
from src.core.model_loader import load_p7  # adjust import to real path
def test_load_p7_has_map_and_params():
    m = load_p7()
    assert m is None or ("failure_part_map" in m and "consumable_params" in m)
```

- [ ] **Step 2: Run, fail.**
- [ ] **Step 3: Implement** `load_p7()` mirroring `load_p6()` (lru_cache, joblib.load from `models_dir / "ml_model_p7_parts_demand.pkl"`, return None if missing). Add to `startup_check`.
- [ ] **Step 4: Run, pass.**
- [ ] **Step 5: Commit.** `git commit -m "feat(p7): register load_p7 in model loader"`

### Task 7: `predict_parts_demand` in predictions.py

**Files:** Modify `app/ml-microservice/src/predictions.py`. Test: `app/ml-microservice/tests/test_predict_parts_demand.py`.

- [ ] **Step 1: Failing test** — fixture machine with known `rul_days`, `failure_type_probs`, a stubbed stock dict → assert returns contract dict with `items`, correct `source`, and falls back to `source="deterministic_fallback"` when `load_p7()` returns None (monkeypatch).
- [ ] **Step 2: Run, fail.**
- [ ] **Step 3: Implement** `predict_parts_demand(machine_id, rul_days, failure_type_probs, horizon_days=30)`:
  - `m = load_p7()`; if None → deterministic path (existing demand_forecast logic) tagged fallback.
  - else: `survival = survival_demand(...)`; `consumable = {pid: croston_forecast(series, ...)*horizon/30 for ...}`; fetch stock dict (injected/queried); `return build_parts_demand(...)`.
- [ ] **Step 4: Run, pass.**
- [ ] **Step 5: Commit.** `git commit -m "feat(p7): predict_parts_demand inference with deterministic fallback"`

### Task 8: Wire routes + unified-health

**Files:** ml-microservice `router.py` (+`/predict/parts-demand`, add to predict-all + batch); backend `demand_forecast.py` (call P7); `app/backend/modules/ml/router.py` (unified-health `parts_demand` block). Tests: backend `test_unified_health_parts_demand.py`.

- [ ] **Step 1: Failing test** — GET unified-health for a seeded machine → response JSON contains `parts_demand` with `items` and `source`.
- [ ] **Step 2: Run, fail.**
- [ ] **Step 3: Implement** route + service calls; reuse `urgency_score` from `demand_forecast.py:35-56`.
- [ ] **Step 4: Run, pass.**
- [ ] **Step 5: Commit.** `git commit -m "feat(p7): expose parts_demand via microservice route + unified-health"`

### Task 9: "Parts Demand" frontend card

**Files:** Create `app/frontend/src/modules/shared/machines/components/PartsDemandCard.tsx`; mount in `MLIntelligenceTab.tsx`. Type for `parts_demand` in the ML prediction type.

- [ ] **Step 1:** Add `parts_demand` to the TS prediction type matching the contract.
- [ ] **Step 2:** Build `PartsDemandCard` (glass + Space Grotesk mono, PartsReadinessCard:164-230 pattern). Show top-N by urgency: reference/name, expected qty, on-hand vs need, "Order N". Plain wording. Empty state "No parts needed in next 30 days."
- [ ] **Step 3:** Mount card in `MLIntelligenceTab.tsx`. Never render "P7".
- [ ] **Step 4: Verify** in browser (`make up`): card renders for a machine with demand.
- [ ] **Step 5: Commit.** `git commit -m "feat(p7): Parts Demand card in ML Intelligence tab"`

**P7.1 GATE:** notebook backtest beats baseline; all pytest green; unified-health returns `parts_demand`; card renders. Update `.session/ml-brainstorm/state.md`.

---

# PHASE P7.2 — Parts-shortage alert routing

### Task 10: Add `PARTS_SHORTAGE` alert type
**Files:** `app/backend/models/alertes.py` (+enum/type value). Test: `test_alertes_parts_shortage.py`.
- [ ] Test: creating an `alertes` row with type `PARTS_SHORTAGE` persists + reads back. → fail → add value → pass → commit.

### Task 11: Emit alert on shortfall
**Files:** new `app/backend/modules/ml/services/parts_alerts.py`; called where P7 result is computed (unified-health path / batch). Test: `test_parts_alerts.py`.
- [ ] Test: P7 result with `shortfall>0` on machine with RUL<horizon → creates ONE `PARTS_SHORTAGE` alert (severity CRITICAL), links `machine_id`; second call doesn't duplicate (dedup per machine+piece until dismissed). → fail → implement (severity rule from spec; reuse alert config thresholds) → pass → commit.

### Task 12: Surface in alert panels
**Files:** `AlertsPanel.tsx`, `ChefTechAlertWorkflow.tsx`. 
- [ ] Render `PARTS_SHORTAGE` alerts with parts-aware text + action link. Verify in browser. Commit.

**P7.2 GATE:** induced shortfall → alert visible to correct role.

---

# PHASE P7.3 — Role-based UX + plain language + explainability

### Task 13: Explainability drawer (shared)
**Files:** Create `app/frontend/src/modules/shared/machines/components/ExplainabilityDrawer.tsx`.
- [ ] Props: machine + parts_demand + role. Renders 4 plain-language sections: Why (RUL + failure type in words) · What if ignored (downtime/rush risk) · What to prepare (parts) · Who acts (role+action). No jargon. Open from PartsDemandCard. Verify. Commit.

### Task 14: ADMIN procurement queue widget
**Files:** admin module (e.g. `app/frontend/src/modules/admin/ProcurementQueue.tsx`) + backend list endpoint aggregating open shortfalls.
- [ ] Test backend aggregation endpoint (machines with shortfall, recommended order). → fail → implement → pass. Build widget with "Approve procurement" (reuse approval flow). Verify. Commit.

### Task 15: CHEFTECH convert-to-intervention/WO action
**Files:** cheftech module + reuse intervention/WO creation endpoints.
- [ ] "Convert prediction → intervention" pre-fills required_pieces from parts_demand. Reuses existing creation. Verify. Commit.

### Task 16: CHETOP business-risk framing + TECHNICIEN prep checklist
**Files:** chetop dashboard tile; technicien dashboard/WO checklist component.
- [ ] CHETOP: machine readiness in business words. TECHNICIEN: "prepare these parts / inspect X" checklist from parts_demand. Verify both. Commit.

### Task 17: Jargon lint
- [ ] grep frontend for banned strings ("Weibull","Croston","probability distribution","feature importance") in user-facing P7 components → none. Commit any fixes.

**P7.3 GATE:** each role correct wording/actions; drawer works; jargon lint clean.

---

# PHASE P7.4 — Guarded auto-draft workflow

### Task 18: Draft creation service
**Files:** `app/backend/modules/ml/services/parts_drafts.py`. Test: `test_parts_drafts.py`.
- [ ] Test: shortfall → creates DRAFT procurement recommendation + draft intervention/WO (status DRAFT/PENDING_APPROVAL) linked to originating `ml_prediction_log` id; NO reservation committed yet. → fail → implement → pass → commit.

### Task 19: Approval path reuse
**Files:** wire draft approval to existing admin validate (`InventoryReservationService.try_reserve()` on approve; release/discard on reject).
- [ ] Test: approve draft → reservation created; reject → draft discarded, nothing reserved. → fail → implement → pass → commit.

### Task 20: Frontend procurement modal
**Files:** `ProcurementRecommendationModal.tsx`.
- [ ] Shows draft, requires explicit human approve/reject. Verify nothing auto-commits. Commit.

**P7.4 GATE:** shortfall → draft created, linked, blocked until human approval.

---

# PHASE P7.5 — Readiness score + timeline + KPIs

### Task 21: Readiness score service
**Files:** Create `app/backend/modules/ml/services/readiness.py`. Test: `test_readiness.py`.
- [ ] Test: `readiness_score(machine)` blends unified_health_score + inventory coverage + technician availability + procurement risk → 0–100, documented equal weights. Edge: missing inputs degrade gracefully. → fail → implement → pass → commit.

### Task 22: Timeline derivation
**Files:** add to `readiness.py` or `timeline.py`. Test: `test_timeline.py`.
- [ ] Test: `machine_timeline(machine_id)` returns ordered events from existing timestamps (ml_prediction_log.created_at, mouvement_stock RESERVED, ordres_intervention.approved_at, ordres_travail status changes, completion). No new table. → fail → implement → pass → commit.

### Task 23: Frontend tiles
**Files:** `ReadinessScoreTile.tsx`, `MaintenanceTimeline.tsx`; mount on dashboards + MachineDetailPage.
- [ ] Render score tile + timeline. Verify. Commit.

### Task 24: KPI endpoint
**Files:** backend KPI aggregation endpoint + dashboard tiles.
- [ ] Test: KPI endpoint returns prevented-downtime proxy, avoided rush orders, stock readiness rate, adoption rate from existing data. → fail → implement → pass → commit. Frontend tiles. Verify. Commit.

**P7.5 GATE:** score tile + timeline render; KPIs compute.

---

# PHASE P7.6 — Feedback closure

### Task 25: Alembic migration — `p7_parts_demand` JSON column
**Files:** new alembic revision on `ml_prediction_log`. Test: `test_ml_prediction_log_p7_column.py`.
- [ ] Test: write+read a row with `p7_parts_demand` JSON. → fail → migration (mirror `p2_failure_types` JSON pattern) → run `alembic upgrade head` → pass → commit.

### Task 26: Persist P7 prediction
**Files:** ShadowLogger / prediction logging path.
- [ ] Test: prediction run logs `p7_parts_demand` JSON into the new column. → fail → implement → pass → commit.

### Task 27: Predicted-vs-actual comparison + retrain queue
**Files:** `ml_retraining.py` (+P7 queue) + completion comparison. Test: `test_p7_feedback.py`.
- [ ] Test: completed intervention with `consumed_pieces` → compares predicted parts vs actual qty_used; records match/error; `ml_retraining.py` queues it (reuse `retrained` flag pattern). → fail → implement → pass → commit.

**P7.6 GATE:** completion → comparison logged → retrain queue picks it up.

---

# Final E2E verification
- [ ] `make up`.
- [ ] Walk ONE machine end-to-end across roles: prediction (Parts Demand card) → PARTS_SHORTAGE alert → admin approves draft procurement → CHEFTECH converts to WO → technician completes with consumed parts → feedback comparison logged → readiness score + timeline reflect the chain.
- [ ] All pytest suites green.
- [ ] Update CLAUDE.md changelog (P7 entry) + `.session/ml-brainstorm/state.md` (all phases checked).

---

## Self-review (done)
- **Spec coverage:** all 6 spec phases map to tasks (P7.1→T1-9, P7.2→T10-12, P7.3→T13-17, P7.4→T18-20, P7.5→T21-24, P7.6→T25-27). ✓
- **Placeholder scan:** P7.1 fully coded; P7.2-P7.6 task breakdowns are intentional (stated in header), each with exact files + test intent + gate — not "TODO/TBD". ✓
- **Type consistency:** `parts_demand` contract identical across Task 4 / Task 8 / Task 26; `failure_part_map` shape consistent Task 2 / Task 5; `load_p7` name consistent Task 6 / Task 7. ✓
