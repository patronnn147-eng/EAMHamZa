The skill is for file-based compression via Python CLI. User provided inline text — I'll apply the compression rules directly.

---

# EAM SagemCom — Project Instructions

## Commands
```bash
# Copy env first (one-time setup)
cp .env.example .env

# Start all services
make up        # → frontend:3000  backend:8000  API docs:8000/docs  MinIO:9000/9001
make down      # Stop all services
make logs      # Tail all logs
make rebuild   # Full clean rebuild
make db        # Connect to Postgres shell

# Jupyter notebooks only
docker compose -f docker-compose.notebooks.yml up --build  # → http://localhost:8888
```

## Project Overview
EAM platform for predictive maintenance of industrial machines.
Full-stack: Next.js frontend, FastAPI backend, ML microservice (Flask/sklearn), Jupyter research notebooks.

## Architecture
- `app/frontend/` — Next.js + TypeScript UI
- `app/backend/` — FastAPI + SQLAlchemy + PostgreSQL
- `app/ml-microservice/` — Flask serving P1-P6 sklearn/XGBoost models
- `app/rag-service/` — RAG service (document ingestion + chat)
- `app/ml-microservice/ml_research/` — Jupyter notebooks for model research (P3 LSTM, P4 anomaly ensemble)
- `app/backend/modules/ml/models/` — trained .pkl files (backend source of truth)
- `app/ml-microservice/models/` — pkl copy used by ml-microservice at runtime

## ML Models
| Name | File | Purpose |
|------|------|---------|
| P1 | `basic_machine_model.pkl` | Failure probability (7 features) |
| P2 | `ml_model_p2_failure_type.pkl` | Failure type classification |
| P3 | `ml_model_p3_rul.pkl` | RUL — XGBoost |
| P4 | `ml_model_p4_anomaly_v2.pkl` | Anomaly detection — 4-method ensemble |
| P5 | `ml_model_p5_priority.pkl` | Work order priority |
| P6 | `ml_model_p6_schedule.pkl` | Maintenance schedule |

## P4 Ensemble (v2) — Critical Details
- Components: Isolation Forest (30%) + Z-Score (20%) + Cluster Deviation (10%) + Autoencoder (40%, optional — needs TensorFlow)
- TensorFlow NOT installed in ml-microservice → autoencoder skipped at runtime, weights renormalized
- pkl must contain: `iso_model`, `weights`, `thresholds`, `training_stats` (mean/std of 5 sensors), `ae_scaler`
- 5 features only: Air temp, Process temp, RPM, Torque, Tool wear
- Score output: 0.0–1.0 (normalized). Threshold: > 0.5 = anomaly
- Frontend card: "Behavioral Anomaly" (NOT "P4") — shows Ensemble Score + Mahal. Distance

## P3 LSTM Hybrid — Critical Details
- Graduate condition: C-index primary (> 62%) AND MAE within 15% of baseline (≤ 16.25 * 1.15)
- Validation split: machines 70-79 held out explicitly (NOT validation_split=0.1)
- XGBoost input: 5 raw sensors only (NOT 52 V3 features)
- History window: 20 cycles

## Model pkl Rules
- Two locations must stay in sync: `app/backend/modules/ml/models/` AND `app/ml-microservice/models/`
- Notebook saves new pkl → copy to `ml-microservice/models/` manually
- v2 pkl takes priority over v1; loader falls back automatically

## Docker
- Jupyter notebooks: `docker compose -f docker-compose.notebooks.yml up --build` → http://localhost:8888
- Notebook dir inside container: `/workspace/app/ml-microservice/ml_research/`
- ROOT path in notebooks: `os.path.abspath('../..')` (2 levels up from ml_research/)
- ml-microservice: standard docker compose

## Key Files
- `app/ml-microservice/src/model_loader.py` — loads all pkl files at startup
- `app/ml-microservice/src/predictions.py` — P1-P6 inference methods
- `app/backend/modules/ml/router.py` — unified-health endpoint, maps ml-microservice response to frontend
- `app/frontend/src/modules/shared/machines/components/MLIntelligenceTab.tsx` — ML card UI
- `app/ml-microservice/ml_research/p4_anomaly_ensemble.ipynb` — P4 research notebook
- `app/ml-microservice/ml_research/p3_lstm_hybrid_rul.ipynb` — P3 research notebook

## Naming Conventions (frontend)
- Never show "P1"–"P6" labels to users
- Use business names: "Failure Probability", "Classification", "RUL Estimate", "Behavioral Anomaly", "Priority", "Schedule"

## Wave 2 Models (DST Fusion)
Advanced models fused via Dempster-Shafer Theory:
- CUSUM, Kalman Filter, Cox PH (survival), Mahalanobis Health Index, PINN, MOMENT (disabled — momentfm not installed)
- Output: `unified_health_score`, `dst_verdict`, BPA beliefs
- Separate from P1-P6; both pipelines run in parallel

## Common Pitfalls
- Jupyter memory overwrites disk patches → close tab before re-patching, reopen from file browser
- Stale pkl with wrong feature count → delete old pkl, notebook retrains on next run
- ml-microservice `MODELS_DIR` points to `app/ml-microservice/models/` NOT `app/backend/modules/ml/models/`
- P4 thresholds use `{name}_min` / `{name}_max` keys (IF uses `if_min`/`if_max`, not `ae_min`)
## Changelog

### 2026-05-14
- P3 LSTM notebook fixed: C-index graduate condition, explicit val split (machines 70-79), raw-only XGBoost input. LSTM graduated MAE=14.95, C-index=0.620
- P4 notebook fixed: stale 7-feature pkl deleted, baseline cell guards feature count mismatch
- notebooks/ folder moved → `app/ml-microservice/ml_research/` (ROOT path updated to `../..`)
- P3/P4 README files added (EN + FR) in `app/ml-microservice/ml_research/`
- P4 ensemble promoted to production (Option B):
  - `ml_model_p4_anomaly_v2.pkl` patched with `training_stats` (mean/std from ai4i2020.csv)
  - `model_loader.py` loads v2 ensemble; extracts iso_model, weights, thresholds, training_stats, ae_scaler (AE optional — TF not installed)
  - `predictions.py` detect_anomaly() rewritten: 5-feature ensemble (IF + Z-score + Cluster + optional AE), score 0.0-1.0
  - `router.py` passes `p4_anomaly_score` to frontend
  - `MLIntelligenceTab.tsx`: MOMENT Anomaly card replaced with "Behavioral Anomaly" card (orange when flagged, shows Ensemble Score + Mahal. Distance)

### 2026-05-30
- P7 Predictive Parts Coordination System — ALL 6 PHASES COMPLETE (branch `clean_Phase_1`)
- P7.1 ML engine:
  - Training notebook `app/ml-microservice/ml_research/p7_parts_demand.ipynb` (7 cells, graduates vs naive baseline)
  - `app/ml-microservice/src/p7_parts_demand.py` — p_fail_within, survival_demand, croston_forecast, build_parts_demand
  - `load_p7()` in `app/ml-microservice/src/core/model_loader.py` (lru_cache, startup_check)
  - `MachineLearningService.predict_parts_demand()` in `predictions.py` — survival+Croston+deterministic fallback
  - `POST /predict/parts-demand` in ml-microservice router; `parts_demand` block in unified-health response
  - `PartsDemandCard.tsx` in `MLIntelligenceTab.tsx` (expand/collapse, "Why?" button)
- P7.2 Alert routing:
  - `AlertType.PARTS_SHORTAGE` added to `models/alertes.py`
  - `app/backend/modules/ml/services/parts_alerts.py` — emit_shortfall_alert (deduped, non-fatal)
  - Wired into unified-health endpoint; Package icon in AlertsPanel for PARTS_SHORTAGE type
- P7.3 Role UX + explainability:
  - `ExplainabilityDrawer.tsx` — Sheet slide-in, 4 plain-language sections (Why/What if/Prepare/Who acts), role-aware via useUserRole()
  - `GET /api/v1/ml/procurement/queue` — list machines with active PARTS_SHORTAGE alerts
  - Jargon lint clean (no Weibull/Croston/ML terms in user-facing P7 UI)
- P7.4 Guarded auto-draft:
  - `app/backend/modules/ml/services/parts_drafts.py` — create_procurement_draft (DRAFT WO), approve (→SUBMITTED), reject (→ANNULÉ), deduped via alert.work_order_id
  - `POST/PATCH/DELETE /api/v1/ml/procurement/draft/*` endpoints
  - `ProcurementRecommendationModal.tsx` — 5-step guarded UI, nothing auto-commits
- P7.5 Readiness score + timeline:
  - `app/backend/modules/ml/services/readiness.py` — compute_readiness_score (4-signal blend: health 40% + inventory 30% + shortage 20% + recency 10%), build_timeline_events
  - `GET /machines/:id/readiness`, `/machines/:id/timeline`, `/kpis` endpoints
  - `ReadinessScoreTile.tsx` + `MaintenanceTimeline.tsx` mounted in MLIntelligenceTab
- P7.6 Feedback closure:
  - Alembic migration `p7_parts_demand_col` — adds `p7_parts_demand Text` column to `ml_prediction_logs`
  - `MlPredictionLog` model + `ShadowLogger` updated to persist p7_parts_demand JSON on every unified-health call
  - `app/backend/modules/ml/services/p7_feedback.py` — compare predicted vs actual parts, augments prediction log with _feedback, wired into technician intervention completion (TERMINÉ/VALIDATED)
- Corrections discovered during execution:
  - Real model loader = `app/ml-microservice/src/core/model_loader.py` (NOT `src/model_loader.py` which is legacy dup)
  - `load_p7` returns WHOLE dict — do NOT use `_extract()` helper
  - `tests/backend/conftest.py` added to fix backend model import path
  - P7 pkl training source: `ordres_intervention.parts_replaced` text (mouvement_stock/pieces/stock CSVs empty)
  - `ordres_intervention.parts_replaced` is a computed property — use `legacy_parts_text` for direct column access
  - 99 tests pass (46 unit/core + 53 backend)

### 2026-05-30 (later)
- RAG migrated from in-memory-only to S3-backed (MinIO bucket `rag-docs`):
  - Alembic migration `rag_s3_storage` — adds `documents.s3_object_key` VARCHAR(512)
  - `app/backend/services/rag_storage.py` — put/get/delete/presign helpers, lazy MinIO client
  - `docker-compose.yml` minio_init now creates `rag-docs` bucket alongside `attachments`
  - Backend routes rewritten in `app/backend/modules/shared/routes/rag_docs.py`:
    * `POST /rag/documents` — single upload, S3 first then ingest, rollback on failure (ADMIN)
    * `POST /rag/documents/bulk` — N files in parallel (max 4 concurrent, 50 total) (ADMIN)
    * `GET  /rag/documents` — list, optional `include_download_url=true` for admin presigned URLs
    * `GET  /rag/documents/{id}/download` — presigned URL (ADMIN)
    * `PUT  /rag/documents/{id}` — replace file, delete old chunks + S3, re-ingest (ADMIN)
    * `DELETE /rag/documents/{id}` — cascade chunks + S3 cleanup (ADMIN)
  - ADMIN role guard enforced server-side; CHEFTECH/TECHNICIEN read-only
  - Frontend `RAGDocuments.tsx` admin UI: drag-drop bulk import, replace, download, English labels

### 2026-06-12
- ML↔RAG chat bridge — built + LIVE-VERIFIED (all smoke layers PASS):
  - `modules/ml/services/chat_context.py` — get_ml_snapshot() reuses get_unified_health route fn, lean dict, never raises
  - `ai_prompts.py` build_ml_context() — French [ETAT ML EN TEMPS REEL] block, sensors labeled NORMAL/ATTENTION/CRITIQUE per machine-category thresholds, K→°C
  - `chat.py` — RAG + ML fetched in parallel (asyncio.gather) when machine_id present; ML block injected just before user question
  - `ChatResponse.ml_context_used: bool` — mechanical injection proof + `[ml_bridge]` INFO log line
  - Frontend: machineId prop on ChatWidget/ChatPage; "Assistant IA" tab on MachineDetailPage
  - Smoke: `app/backend/scripts/smoke_ml_rag_bridge.py` (3 layers, BRIDGE/LLM verdicts split, --allow-destructive gates docker stop, exit 0/1/2)
  - Discovered: ML container down ≠ no context — RULCalculator rule-based fallback (score_source=fallback_additive) still injects valid block; safety property = "answers without error"
  - Login API field is `mot_de_passe` (not `password`); machines list = `/api/v1/entities/machines`

### 2026-07-19 — Phase 4 (Model Redesign), sub-phases 4.1/4.2/4.3(partial)/4.6
Per `docs/ML_MODEL_ROADMAP_P1_P7.md` Master Roadmap. 4.4/4.5 remain hard-blocked (no real non-synthetic ground truth yet).

- **4.1 Reporting hygiene**:
  - `model_registry.py`: every model now carries `validation_status` (`leaked`/`unverified`/`group-holdout-validated`) — P1/P2/P5 hardcoded `leaked` regardless of methodology (a better split can't fix a label formula), P4/P6/P7 default `unverified`, P3 dynamic based on whether the last retrain actually used group-holdout.
  - `ml_retraining.py`: P2/P5 now get a repeated group-holdout pass (up to 5 folds across different held-out machines) reporting `val_f1_macro_mean`/`_std`/`n_folds` — a no-op today (zero real ground truth in this environment) but activates automatically once real data accumulates, same "prepared and shelved" pattern as P1's contextual features.
  - `ModelHealthTable.tsx`: colored trust badge per model, plain-French tooltip (no ML jargon), replacing the old all-numbers-look-equal display.
- **4.2 P3 uncertainty**:
  - Production: P3 retrain now also fits an XGBoost quantile-regression head (`reg:quantileerror`, `quantile_alpha=[0.1,0.5,0.9]`) alongside the existing point estimator — separate `quantile_model`/`quantile_levels` keys in the pkl, best-effort (point model still ships if this fails). `core/model_loader.py` gets `load_p3_quantile()`; `predictions.py` gets `predict_rul_interval()`; `rul_calculator.py` rescales the raw model's relative spread onto the final blended `rul_days` (not the raw model output) as `rul_confidence_interval: {low, high, confidence: 0.8}`. `MLIntelligenceTab.tsx`'s RUL card now shows a real range instead of a hardcoded fake "±0.8d".
  - Research prototype (not production): `app/ml-microservice/ml_research/p3_cox_weibull_prototype.py` — Cox PH / Weibull AFT with explicit right-censoring vs. a naive censoring-blind regression baseline, same 100-machine/train<70/test≥80 convention as `p3_lstm_hybrid_rul.ipynb` so C-index is comparable. **Real executed result: Weibull AFT C-index 0.714, Cox PH 0.712, naive baseline 0.644** — censoring-aware modeling genuinely wins, supports the roadmap's medium-term Cox/Weibull recommendation.
- **4.3 P4 — fully complete**:
  - `p4_feedback.py` (new, mirrors `p7_feedback.py`) + migration `p4_wo_outcome_column` (`ml_prediction_logs.p4_wo_outcome` Text) — on WO completion, looks back up to 14d for the most recent unmatched real anomaly flag on that machine and marks it confirmed. Precision-side signal only (recall/full backtest is Phase 5). Wired into the same TERMINÉ/VALIDATED hook as P7.
  - TensorFlow + real Autoencoder re-enable — user freed disk (426MB→15GB) mid-session. Root cause found by inspection: the live `ml_model_p4_anomaly_v2.pkl` already carried `weights['ae']=0.4`, `thresholds['ae_max']`, and an `ae_scaler`/`autoencoder_path` from an earlier `p4_anomaly_ensemble.ipynb` run — an AE was trained once, but its `.keras` artifact was never persisted to this host's `models/` dirs (`autoencoder_path` pointed at a stale `/workspace/...` Jupyter-container path that doesn't exist here). Also confirmed a real bug in `core/model_loader.py`'s `load_p4()`: it read `data.get("autoencoder")` (a nonexistent embedded key) instead of resolving `autoencoder_path` — the legacy `src/model_loader.py` already had the correct lazy-load-by-path logic, ported into the authoritative loader as `_load_p4_autoencoder()` (guarded `try/except ImportError`, resolves by `os.path.basename` against `config.models_dir` so the path is portable across hosts/containers).
  - Retrained the AE from scratch in an isolated venv (`tensorflow-cpu==2.20.0`, pinned exactly matching `requirements-heavy.txt` so the artifact and runtime are the same TF build) — same architecture as the original notebook (5→16→8→4→8→16→5 dense, healthy-only `Machine failure==0` rows, MSE loss, EarlyStopping) — and recomputed `ae_max` fresh against the new AE's own error distribution rather than reusing the orphaned frozen threshold. IF/Z-score/cluster weights and thresholds left untouched. Verified before deploying: normal reading → 0.0144 normalized, synthetic outlier → 1.0.
  - `tensorflow-cpu==2.20.0` added to `app/ml-microservice/requirements-heavy.txt`, image rebuilt (`docker compose build ml-service`), container recreated — startup log confirms `[OK] P4 autoencoder loaded (TF available)`. Live-verified via `GET /api/v1/ml/predict/anomaly`: normal reading → `anomaly_score: 0.016`, outlier → `1.0`, both through the real production ensemble path (not a standalone script).
  - Backend and frontend images also rebuilt this pass (`docker compose build backend frontend`) — all of 4.1/4.2/4.3's changes are now baked into the running images, not just docker-cp'd. All three containers healthy post-recreate.
- **4.6 P6 status correction**: fully covered by 4.1's `validation_status` mechanism — P6 shows `unverified` in `model_registry.py`'s default map, hard-skip untouched. No separate work needed.
- **Side effect, caught and reverted**: an errant global `pip install tensorflow-cpu` (before realizing this machine's Python is a shared multi-tool environment, not project-isolated) bumped `protobuf` to 7.35.1 and silently dropped `google-auth`, breaking `google-generativeai`/`streamlit`/`autogen-core` pins. Reverted (`protobuf~=5.29.3` restored, `google-auth` reinstalled, verified `import google.generativeai` works again) before doing anything further. Lesson: use an isolated venv for any future ad-hoc Python package installs on this host, never the global env.

### 2026-07-20 — Healthy telemetry seed generator
- New `app/backend/seed_ml_data_healthy.py` — mirrors `seed_ml_data_all.py`'s Planning→ITV→OT→Telemetry+shadow-log chain (same schema/relationships/is_synthetic flag), but every cycle simulates normal operation instead of degradation.
  - Sensor bands grounded in `ai4i2020.csv` full-dataset mean/std (air 300±2K, process 310±1.5K, rpm 1539±179, torque 40±10Nm) — keeps healthy readings close to the training distribution.
  - Tool wear: per-machine seeded choice of "sawtooth" (rises 3-10→45-70min per cycle, resets — mimics preventive tool service) or "flat" (baseline ±noise), always <90min hard ceiling — well under the 100min threshold `_failure_prob()`/P4 thresholds treat as risk, and drawn stationary per-cycle (no across-cycle trend) so nothing reads as a degradation arc.
  - `failure_type="NONE"`, `priority="BASSE"`, `itv_type="PREVENTIVE"` always; shadow log `risk_level="LOW"`, `is_anomaly=False`.
  - CLI: `--clean`, `--cycles`, `--machines 1,2,3` (subset filter).
  - `seed_ml_data_all.py` got one additive, backward-compatible `--machines` filter arg (default: all, same behavior as before) so a mixed fleet can be built by running each script against a disjoint machine-id subset.

### 2026-07-20 (later) — Placeholder-telemetry bug: identical ML numbers on every machine
- **Symptom**: `/machines/:id` showed the same values for every machine — Air 300.0 K, Process 310.0 K, 1500 RPM, 40.0 Nm, 0 min wear, health 65, RUL 16d, schedule 9d, same P7 parts list.
- **Root cause (two layers, models were fine)**:
  1. `_get_telemetry_history` filters `is_synthetic.is_(False)`; DB holds 480 telemetry rows, 100% `is_synthetic=true` → zero entries for every machine.
  2. Both ML read paths then substituted hardcoded placeholders `(300.0, 310.0, 1500, 40.0, 0.0)` (`router.py`, `rul_calculator._extract_telemetry`) and still called the models — identical input ⇒ identical output fleet-wide. Verified directly: `POST /api/v1/ml/predict-all` on those placeholders returns exactly the UI's numbers.
- **Fix 1 — no silent placeholder defaults**: new `_latest_sensors()` returns all-None when there is no telemetry; `_extract_telemetry` likewise. When telemetry is absent the ml-microservice is **not** called at all (predictions on fabricated sensors are meaningless), health falls back to the maintenance-history-only `fallback_additive` path, and the response carries `telemetry_available: false` + `telemetry_data_points: 0`, null sensor fields, empty `sensor_status`.
- **Fix 2 — dev toggle**: `settings.ml_allow_synthetic_telemetry` (env `ML_ALLOW_SYNTHETIC_TELEMETRY`, default **false**, wired in `docker-compose.yml` + `.env.example`). When true, `_get_telemetry_history` drops the `is_synthetic` filter so seeded data drives the models in local dev; quarantine stays on everywhere else.
- **Frontend** `MLIntelligenceTab.tsx`: amber "No sensor data for this machine" banner, header switches to "Neural Engine Idle — No Sensor Data" / "Models Idle". Sensor tiles already rendered `—` for null.
- **Verified**: flag off → `telemetry_available:false`, all sensors null, per-machine health now differs (88.0 / 87.5, `score_source: fallback_additive`). Flag on → 120 points/machine, distinct readings (298.54K/1562rpm vs 297.42K/1482rpm), `score_source: dst_fusion`. Backend + frontend images rebuilt and recreated; `tsc --noEmit` clean.
- Left alone on purpose: `POST /machines/{id}/telemetry` (manual simulator) still defaults optional fields to 300/310/1500 — that's a user-initiated write, not a silent read fallback.

### 2026-08-01 — AKS production migration: Phase 0 complete, Phase 1 planning started
Per `docs/superpowers/specs/2026-07-30-aks-production-migration-design.md` (design) and `docs/superpowers/plans/2026-07-30-aks-phase0-foundations.md` (Phase 0 plan). Subscription is **Azure for Students** (`ESPRIT` tenant) — a one-time ~$100 credit, not recurring billing; whole effort framed as POC-and-validate, not a permanent production cutover.

- **Phase 0 (Foundations) — done, verified, live.** `infra/terraform/*.tf` provisions everything via Terraform, committed to `Phase_2`, pushed to both `origin` (GitHub) and `gitlab` (GitLab):
  - Resource group `eam-prod-rg`, VNet/subnet, AKS cluster `eam-prod-aks`, Azure Database for PostgreSQL Flexible Server `eam-prod-psql-1a6mi7` (pgvector `0.8.2` verified), Key Vault `eam-prod-kv-h597b3` (holds the Postgres admin password).
  - **Deviated from the spec's original plan** (ARM64 nodes in `germanywestcentral`) because real subscription constraints only surfaced during execution: `Total Regional vCPUs` is capped at 6 for this subscription in *every* region checked (10 regions, identical cap — a subscription-wide default, not regional); a subscription-level Azure Policy (`sys.regionrestriction`) locks deployment to exactly 5 regions (switzerlandnorth/spaincentral/germanywestcentral/norwayeast/polandcentral); none of the 4 non-Germany regions offer any ARM64 VM SKU for this subscription; `germanywestcentral`'s quota stayed stuck at 4/6 used (by the old demo VM) even after deallocating it. Landed on: **x86** (`Standard_B2s_v2`), **`polandcentral`**, 1 system node + 1-2 user nodes (autoscaling).
  - Old demo VM (`eam-demo-vm`) was **deallocated** (stopped, not deleted) to free quota during troubleshooting — currently offline, disk/config intact.
  - Terraform state migrated from an Azure Blob backend to **HCP Terraform** (`app.terraform.io/app/eam-sagemcom/workspaces/aks-phase0`) purely to get a viewable web dashboard — bookkeeping-only move, verified via `terraform plan` → `No changes.` before and after. Workspace Execution Mode is **Local** (HCP's remote runners have no `az` CLI and this tenant blocks Service Principal creation for regular users, so Remote mode can't work here).
  - Known unresolved local-environment quirk: on the user's Windows machine, Terraform's own subprocess call to `az` fails even though the user's shell resolves `az` directly fine (PATH/PATHEXT ruled out as cause). Workaround in use: Claude runs `terraform plan`/`apply` from its own working session; user verifies via Azure Portal + the HCP Terraform dashboard.
- **Phase 1 (app deployment onto the cluster) — brainstorming in progress, not yet at a written design doc.** Confirmed so far: full plan→files→deploy flow like Phase 0 (not files-only); all ~7 app pieces at once (backend, frontend, ml-service, rag-service, celery_worker, celery_beat, rabbitmq); a **new** CI job builds **x86/amd64** images (existing `:demo` CI jobs stay ARM64, untouched, for the old demo VM). Still open when the session paused: namespace strategy (one namespace vs. staging-first), Key Vault→pod secrets wiring, ingress/cert-manager setup. See memory `aks-phase0-build.md` for full resume detail.

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current
