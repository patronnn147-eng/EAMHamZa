# C9 — MLOps Loop (Registry + Drift + Guarded Retraining) — Design Spec

Date: 2026-06-19
Status: Approved (pending written-spec review)
Source: `presentation/blueprint/EAM_FEATURE_BLUEPRINT.md` → Part C9
Sequence: Part C item 2 of 8 (C10 ✅ → **C9** → C8 → C4 → C5 → C3 → C6 → C7)

## 1. Goal

Give the platform an operational MLOps surface: a model registry that detects pkl divergence between the two model directories, drift detection over logged predictions, and a **guarded** (ADMIN-triggered, never automatic) retraining trigger — all behind one read-only ADMIN endpoint plus a dashboard, with a CI check that fails builds on model divergence.

## 2. Current State (grounded)

- Two model dirs, **already diverged**: `app/backend/modules/ml/models/` has `feature_pipeline_v3.pkl`, `ml_model_p3_lstm_only.pkl`; `app/ml-microservice/models/` has a legacy `ml_model_p4_anomaly.pkl`. The documented pitfall is live.
- `app/backend/models/ml_prediction_log.py` — `ml_prediction_logs` table: `machine_id`, `risk_level`, `failure_probability`, `rul_days`, `is_anomaly`, `anomaly_score`, sensor columns (`air_temperature`, `process_temperature`, `rotational_speed`, `torque`, `tool_wear`), `created_at`. Populated by `ShadowLogger` (`modules/ml/logging.py`) on every unified-health call.
- `modules/ml/services/ml_retraining.py` — `RetrainingService.run_retraining_pipeline(db, model_type='all')` already: fetches `Ordres_intervention.retrained==False` ground truth, holds out 20% val, **accuracy-gates to reject regressions**, `_backup_model`, saves, marks `retrained=True`, `_cleanup_old_versions`. `get_retraining_stats(db)` → `{new_data_points}`.
- `core/ml_client.get_model_metrics()` → calls ml-microservice `/model/metrics` (accuracy etc.), returns `{success, ...}` or `{success: False, error}`.
- ADMIN dashboard exists: `app/frontend/src/modules/admin/ml/MLDashboard.tsx`.

## 3. Architecture — three pure cores + endpoints + dashboard + CI

### 3a. `modules/ml/services/model_registry.py`
- `MODEL_CATALOG`: list of `{key, label, filename}` — business labels (no P-codes): "Probabilité de panne" → `basic_machine_model.pkl`, "Détection d'anomalie" → `ml_model_p4_anomaly_v2.pkl`, etc.
- `_file_hash(path) -> str | None` (sha256, None if absent).
- `scan_models(backend_dir, micro_dir) -> list[dict]`: per catalog model `{key, label, filename, in_backend, in_micro, hash_match, size_backend, mtime_backend}`. Pure given two dir paths → testable with temp dirs.
- `check_sync(backend_dir, micro_dir) -> list[dict]`: divergences only — `{filename, reason}` where reason ∈ `missing_in_microservice | missing_in_backend | hash_mismatch`. Reused by the endpoint AND the CI script.

### 3b. `modules/ml/services/drift.py`
- `population_stability_index(baseline: list[float], recent: list[float], bins=10) -> float` (standard PSI). Pure.
- `compute_drift(baseline_rows, recent_rows, sensors) -> dict`: per sensor `{psi, mean_shift_pct, status}` where `status = stable (psi<0.1) | watch (0.1≤psi<0.25) | drifting (psi≥0.25)`; overall `verdict = max severity`. Pure — takes two lists of row dicts (from `ml_prediction_logs`) → testable with synthetic stable vs shifted data.
- The route supplies rows: baseline = older window (e.g. rows 30–60 days old), recent = last 14 days, from `ml_prediction_logs`.

### 3c. `modules/ml/services/retraining_advisor.py`
- `recommend_retraining(new_data_points: int, drift_verdict: str, min_points: int = 50) -> dict`: `{recommended: bool, reasons: list[str]}`. Recommends when `new_data_points >= min_points` OR `drift_verdict == 'drifting'`. Pure, deterministic.

### 3d. Endpoints — `modules/ml/router.py` (or a new `routes/mlops.py`), ADMIN-guarded
- `GET /api/v1/ml/model-health` → `{ models: scan_models(...), divergences: check_sync(...), metrics: get_model_metrics(), drift: compute_drift(...), retrain: recommend_retraining(...) }`. ADMIN role enforced server-side (raise 403 otherwise). Never raises on data gaps — each block degrades to empty/partial.
- `POST /api/v1/ml/retrain` (body `{model_type?: str}`) → ADMIN-guarded; calls `RetrainingService.run_retraining_pipeline(db, model_type)` and returns its result. **No automatic invocation anywhere.**

### 3e. pkl-sync CI — `app/backend/scripts/check_model_sync.py`
Reuses `check_sync()`; prints divergences; `sys.exit(1)` if any, else `0`. Intended for CI (a diverged commit fails the build). Standalone, runnable locally.

### 3f. Frontend — `MLDashboard.tsx` (ADMIN)
- `ModelHealthTable` component: fetches `/model-health`, renders the registry table (sync status badge, last-trained, accuracy, drift badge per model) + a top divergence banner when any.
- Guarded **Retrain** button → confirm modal → `POST /ml/retrain` → toast result. Plain-language labels.

## 4. Decisions
- **Guarded, never auto-retrain.** Recommendation badge + ADMIN button only. `run_retraining_pipeline` already backs up + accuracy-gates. (Auto-on-drift rejected: runaway-retraining risk.)
- **Drift baseline** = rolling windows from `ml_prediction_logs` (self-contained); not the microservice P4 stats.
- **Drift metric** = PSI + mean-shift (standard, explainable).
- Reuse existing `RetrainingService` and `get_model_metrics` — no new training/metrics code.

## 5. Error Handling
- `/model-health` never raises: missing dir → empty list; metrics service down → `metrics.success=false` passed through; too few log rows for drift → `verdict: insufficient_data`.
- `/retrain` surfaces the pipeline's own `{message, models_retrained}`; on exception returns 500 with the error (ADMIN-only, acceptable).
- `scan_models` tolerates absent files (None hash → `in_*: false`).

## 6. Testing
- `model_registry`: `scan_models` + `check_sync` with temp dirs — identical files (hash_match true, no divergence), differing bytes (hash_mismatch), missing file (missing_in_microservice).
- `drift`: `population_stability_index` ~0 for identical, large for shifted; `compute_drift` returns `stable` for same distribution, `drifting` for a clear mean shift; `insufficient_data` when rows empty.
- `retraining_advisor`: recommends on `new_data_points>=min` and on `drift_verdict=='drifting'`; not otherwise.
- Endpoint: ADMIN guard returns 403 for non-admin (smoke).

## 7. Out of Scope (later)
- Full experiment tracking (MLflow), model lineage UI, A/B shadow comparison beyond existing logs, scheduled cron retraining (manual trigger only this round).
