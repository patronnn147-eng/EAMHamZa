# EAM SagemCom — Project Instructions

## Project Overview
Enterprise Asset Management (EAM) platform for predictive maintenance of industrial machines.
Full-stack: Next.js frontend, FastAPI backend, ML microservice (Flask/sklearn), Jupyter research notebooks.

## Architecture
- `app/frontend/` — Next.js + TypeScript UI
- `app/backend/` — FastAPI + SQLAlchemy + PostgreSQL
- `app/ml-microservice/` — Flask serving P1-P6 sklearn/XGBoost models
- `app/ml-microservice/ml_research/` — Jupyter notebooks for model research (P3 LSTM, P4 anomaly ensemble)
- `app/backend/modules/ml/models/` — trained .pkl model files (source of truth for backend)
- `app/ml-microservice/models/` — copy of pkl files used by ml-microservice at runtime

## ML Models
| Name | File | Purpose |
|------|------|---------|
| P1 | `basic_machine_model.pkl` | Failure probability (7 features) |
| P2 | `ml_model_p2_failure_type.pkl` | Failure type classification |
| P3 | `ml_model_p3_rul.pkl` | Remaining Useful Life (RUL) — XGBoost |
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
- When notebook saves new pkl → copy to ml-microservice/models/ manually
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
- `app/frontend/src/modules/shared/machines/components/MLIntelligenceTab.tsx` — machine detail ML card UI
- `app/ml-microservice/ml_research/p4_anomaly_ensemble.ipynb` — P4 research notebook
- `app/ml-microservice/ml_research/p3_lstm_hybrid_rul.ipynb` — P3 research notebook

## Naming Conventions (frontend)
- Never show "P1", "P2", "P3", "P4", "P5", "P6" labels to users
- Use business names: "Failure Probability", "Classification", "RUL Estimate", "Behavioral Anomaly", "Priority", "Schedule"

## Wave 2 Models (DST Fusion)
Advanced models fused via Dempster-Shafer Theory:
- CUSUM, Kalman Filter, Cox PH (survival), Mahalanobis Health Index, PINN, MOMENT (disabled — momentfm not installed)
- Output: `unified_health_score`, `dst_verdict`, BPA beliefs
- These are separate from P1-P6; both pipelines run in parallel

## Common Pitfalls
- Jupyter memory overwrites disk patches → always close tab before re-patching, then reopen from file browser
- Stale pkl with wrong feature count → delete old pkl, notebook retrains automatically on next run
- ml-microservice MODELS_DIR points to `app/ml-microservice/models/` NOT `app/backend/modules/ml/models/`
- P4 thresholds use `{name}_min` / `{name}_max` keys (IF uses `if_min`/`if_max`, not `ae_min`)
