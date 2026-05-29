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
