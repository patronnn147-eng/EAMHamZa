# Codebase Concerns

**Analysis Date:** 2026-05-05

---

## Fixed During This Session (reference)

Issues resolved; documented here so future work doesn't re-introduce them.

**Concurrency — Kalman singleton shared across requests:**
- Was: module-level `_kalman_estimator` mutated by every `predict_all()` call
- Fixed: `KalmanStateEstimator()` instantiated fresh per request in `app/ml-microservice/src/predictions.py`

**Concurrency — CUSUM stateful predict():**
- Was: `AnomalyEnsemble.predict()` updated `CUSUMDetector` state in-place; concurrent requests corrupted each other
- Fixed: `predict_with_history()` stateless method in `app/ml-microservice/src/anomaly_cusum.py`

**Concurrency — SurvivalModel fitting on shared singleton:**
- Was: `fit_from_logs()` called on global instance per request
- Fixed: fresh `SurvivalModel()` per request when fitting from logs; global used read-only as pretrained fallback

**Kalman F matrix wrong + no dt support:**
- Was: `F[0,:] = [1,-1,0]` → `HI -= RUL` (drops 30pts if RUL=30); no elapsed-time parameter
- Fixed: `F[0,:] = [1,0,-dt]`, `update(dt)`, `smooth_from_scores` reads `obs["dt"]` from entries; `predictions.py` computes real dt from `created_at` timestamps
- Files: `app/ml-microservice/src/kalman_estimator.py`, `app/ml-microservice/src/predictions.py`

**DST BPA hard threshold cliff:**
- Was: binary mass assignment at HI=80/50 caused discontinuous score jumps
- Fixed: piecewise-linear soft BPA in `app/ml-microservice/src/dst_fusion.py`

**Drift detection false positives:**
- Was: PSI at n<500 was unreliable; PSI drove `feature_drift` flag
- Fixed: `feature_drift = ks_drift` only (KS test calibrated by sample size); PSI informational
- File: `app/ml-microservice/src/drift_detector.py`

**SHAP explainer rebuilt every call:**
- Was: new `TreeExplainer` per predict request (~100-500ms overhead)
- Fixed: module-level `_explainer_cache` keyed by `id(model)` in `app/ml-microservice/src/xai_service.py`

**P2/P3/P5 retraining bypassed backup-rollback:**
- Was: early `joblib.dump + continue` skipped the safety net P1/P4 used
- Fixed: all training inside backup→validate→rollback block in `app/backend/modules/ml/services/ml_retraining.py`

**TTLCache unbounded memory growth:**
- Was: `set()` never evicted; `clear_expired()` existed but never called automatically
- Fixed: bounded to `_MAX_ENTRIES=1000`; evicts expired entries at capacity, drops oldest if still full
- File: `app/ml-microservice/src/cache.py`

**Backend duplicate ML inference code:**
- Was: `backend/modules/ml/predictions.py` + `model_loader.py` duplicated microservice logic; local models loaded in backend process
- Fixed: deleted `predictions.py`, `model_loader.py`, `services/ml_xai.py` from backend; `RULCalculator` uses only `fusion_result` from microservice
- Files deleted: `app/backend/modules/ml/predictions.py`, `app/backend/modules/ml/model_loader.py`, `app/backend/modules/ml/services/ml_xai.py`

**Shadow log bug — `AttributeError` on every prediction:**
- Was: `router.py:280` called `MachineLearningService.create_shadow_log()` — method doesn't exist on that class
- Fixed: `ShadowLogger.create_shadow_log()` from `app/backend/modules/ml/logging.py`

**Dead import in alertes.py:**
- Was: `from modules.ml.ml_predictive import MachineLearningService` — file never existed
- Fixed: uses `RULCalculator` + `ml_client` in `app/backend/services/alertes.py`

**lifespan defined after FastAPI() call:**
- Was: `NameError: name 'lifespan' is not defined` at startup
- Fixed: `lifespan` function moved before `app = FastAPI(...)` in `app/ml-microservice/main.py`

**SHAP computed on every predict_all call (opt-in now):**
- Was: SHAP explanations always computed (+50-200 ms); callers that ignored them paid full cost
- Fixed:  field on  in ;  gates SHAP block;  endpoint passes 
- Files: , , , 

** query no limit (500-row cap applied):**
- Was: fetched ALL telemetry rows per prediction request
- Fixed:  + Python reverse in 
- File: 

**Fleet dashboard N+1 query (single JOIN applied):**
- Was: O(N) per-machine intervention queries in  and 
- Fixed: single , grouped by  in Python; passed as pre-fetched map to 
- File: 

**Retraining accuracy gate (80/20 val split + F1/R2 threshold):**
- Was: any model that loaded and had features was accepted; regressions went undetected
- Fixed: 80/20 stratified train/val split; classifiers require F1 >= 0.70 on val set; P3 regressor requires R2 >= 0.40; models failing gate are rejected and backup restored
- File: 

---

## Remaining Tech Debt

**`_parse_ts` closure defined inside hot path:**
- Issue: `_parse_ts()` function defined inside `predict_all()` every call (inside the `if len(logs) >= 2` block)
- Files: `app/ml-microservice/src/predictions.py` (Kalman history section)
- Impact: minor — Python function creation is cheap; no correctness issue
- Fix: hoist to module-level helper or add to `FeatureStore`
- Priority: Low

**`ModelRegistry` singleton initializes at import time:**
- Issue: `registry = ModelRegistry()` at module level triggers `_load_from_disk()` on every import, even if registry never used
- Files: `app/ml-microservice/src/model_registry.py:146`
- Impact: startup I/O; fails silently if `MODEL_REGISTRY_PATH` is not writable (swallowed in `except`)
- Fix: lazy initialization — create registry instance on first use
- Priority: Low

**`ml_retraining.py` MODELS_DIR uses 5-level dirname chain:**
- Issue: `os.path.dirname` called 5x as path to microservice models dir — breaks if file is moved
- Files: `app/backend/modules/ml/services/ml_retraining.py:14-20`
- Impact: retraining silently writes to wrong path if directory structure changes
- Fix: use only `ML_MODELS_DIR` env var (already supported); remove fragile fallback path; add startup assertion
- Priority: Medium

**P6 retraining permanently skipped:**
- Issue: `ml_retraining.py` skips P6 with `"reason": "P6 requires actual maintenance scheduling outcomes"`
- Files: `app/backend/modules/ml/services/ml_retraining.py:217-225`
- Impact: P6 model never improves from production data
- Fix: expose `next_maintenance_date` from planning schema; add ground truth capture to work order completion flow
- Priority: Medium (deferred by design — schema gap)

**RUL proxy for P3 training is crude:**
- Issue: `_rul_proxy = (max_wear - tool_wear) / 60` used as RUL label — linear assumption, ignores failure mode
- Files: `app/backend/modules/ml/services/ml_retraining.py:209-216`
- Impact: P3 model learns simplified degradation curve; overestimates RUL for non-wear failures
- Fix: use actual time-to-failure from closed work orders as RUL ground truth
- Priority: Medium

**Priority proxy for P5 training is inverted:**
- Issue: label 0 = "machine failed + high wear" (most critical) but `_p5_labels = ['P1','P2','P3']` maps 0→P1; P1 is highest priority label — this is actually correct, but the logic path `failure=1 AND wear>=75%` → label 0 while `failure=1 AND wear<75%` → label 1 creates inconsistent priority assignment
- Files: `app/backend/modules/ml/services/ml_retraining.py:230-241`
- Impact: P5 priority predictions may be unreliable under mixed failure scenarios
- Fix: derive labels from actual work order priority field once captured
- Priority: Low-Medium

**`alertes.py` imports inside loop body:**
- Issue: `from modules.ml.rul_calculator import RULCalculator` inside `for machine in machines` — resolved from cache each iteration but is bad practice and obscures dependencies
- Files: `app/backend/services/alertes.py:261-262`
- Impact: none at runtime (Python caches imports); code clarity issue
- Fix: move imports to top of file or top of method
- Priority: Low

---

## Security Considerations

**CORS default allows backend origin only:**
- `ALLOWED_ORIGINS` defaults to `http://backend:8000`
- Risk: dev environments may set `ALLOWED_ORIGINS=*` and forget to restrict in staging
- Files: `app/ml-microservice/main.py:33`
- Recommendation: validate `ALLOWED_ORIGINS` is not `*` in production via startup assertion

**Rate limiter state is in-memory only:**
- `RateLimiter` in `app/ml-microservice/src/rate_limiter.py` uses dict — resets on restart; not shared across multiple microservice replicas
- Risk: rate limits ineffective under horizontal scaling or frequent restarts
- Mitigation: acceptable for current single-replica deployment; use Redis for multi-replica

**`technician_id=0` for simulation entries:**
- `app/backend/modules/ml/router.py` uses `SYSTEM_TECHNICIAN_ID` env var (default 0)
- Risk: if DB has FK constraint on technician_id, default 0 causes insert failure; simulation endpoint silently broken
- Fix: create system user in DB seed; set `SYSTEM_TECHNICIAN_ID` in compose env

---

## Performance Bottlenecks

**`MachineTelemetry` query in `_get_telemetry_history` — no limit:**
- Fetches ALL telemetry rows for a machine with no pagination
- Files: `app/backend/modules/ml/router.py` (`_get_telemetry_history` helper)
- Impact: machines with years of telemetry → large result set per prediction request
- Fix: add `.limit(500)` — microservice only uses last 500 entries via `_MAX_LOGS`
- Priority: Medium

---

## Fragile Areas

**`MahalanobisHealthIndex` requires 11+ logs:**
- Falls back to `health_index=100` (perfect health stub) with <11 log entries
- Files: `app/ml-microservice/src/health_index.py`, `app/ml-microservice/src/predictions.py:297`
- Why fragile: new machines always start with stub score; DST fusion filters it via `score_source` check but boundary is not obvious
- Safe modification: always check `score_source not in ("no_model", "fallback")` before using Mahal output

**`SurvivalModel.fit_from_logs` threshold at 10 logs:**
- Silently returns without fitting if `len(logs) < 10`
- Files: `app/ml-microservice/src/survival_model.py`
- Why fragile: `_fitted` stays False; caller must check before calling `predict()`; current code does check but fragile contract
- Safe modification: always guard with `if local_surv._fitted:` as currently done in `predictions.py`

**Baseline persistence path uses env var with relative default:**
- `DRIFT_BASELINE_PATH` defaults to `../drift_baseline.json` relative to `src/`
- Files: `app/ml-microservice/src/drift_detector.py:31-34`
- Why fragile: relative paths resolve differently when running tests vs Docker
- Fix: use absolute path with `os.getenv("DRIFT_BASELINE_PATH", "/data/drift_baseline.json")`

---

## Missing Critical Features

**No model versioning in production:**
- `model_registry.py` exists but `register()` is never called during training or deployment
- Blocks: rollback to previous model version; A/B testing; audit trail
- Files: `app/ml-microservice/src/model_registry.py`

**No alert deduplication:**
- `alertes.py` creates new alert records every run without checking for existing open alerts
- Blocks: prevents alert spam for persistent failures
- Files: `app/backend/services/alertes.py`

---

## Test Coverage Gaps

**No tests for Wave 2 DST fusion pipeline:**
- `dst_fusion.py`, `kalman_estimator.py`, `survival_model.py`, `health_index.py` have zero test coverage
- Files: `app/ml-microservice/src/dst_fusion.py`, `app/ml-microservice/src/kalman_estimator.py`
- Risk: F matrix bugs, BPA normalization errors, fusion edge cases go undetected
- Priority: High

**No integration test for `predict_all` end-to-end:**
- Only unit test exists: `tests/backend/test_ml_prediction.py` (P1 model only)
- Risk: microservice startup failures, endpoint contract changes, serialization errors undetected
- Priority: High

**No test for drift detector:**
- KS test + PSI logic untested; false positive/negative behavior unknown
- Files: `app/ml-microservice/src/drift_detector.py`
- Priority: Medium

**Retraining pipeline untested:**
- `run_retraining_pipeline` has complex branching (P1-P5 models, backup/rollback, DB marking)
- Zero test coverage means backup/rollback logic could silently break
- Files: `app/backend/modules/ml/services/ml_retraining.py`
- Priority: Medium

---

*Concerns audit: 2026-05-05*
