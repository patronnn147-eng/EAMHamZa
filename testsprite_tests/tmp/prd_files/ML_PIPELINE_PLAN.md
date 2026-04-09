# ML Pipeline Plan — EAMSagemCom
> **Purpose:** This file is the entry point for Claude Code (and any developer) to understand the full ML strategy of this project. Read this first before touching any ML file.

---

## Project Context

**EAMSagemCom** is an Enterprise Asset Management platform for **Sagemcom**. The ML engine adds predictive intelligence on top of the core EAM features (machines, work orders, technicians, plannings).

**Backend ML service:** `app/backend/modules/ml/`
**Trained model (P1):** `basic_machine_model.pkl`
**Training dataset:** `ai4i2020.csv` (Kaggle AI4I 2020 — 10,000 rows)

---

## 6 ML Problems Defined for This Project

| # | Problem | Type | Priority |
|---|---|---|---|
| P1 | Binary failure prediction | Classification | ✅ In production |
| P2 | Failure type (TWF/HDF/PWF/OSF/RNF) | Multi-label | 🔴 Next |
| P3 | Remaining Useful Life (RUL) estimation | Regression | 🔴 Next |
| P4 | Anomaly detection | Unsupervised | 🟡 Medium |
| P5 | Work order priority prediction | Multi-class | 🟡 Medium |
| P6 | Maintenance schedule optimization | Time-series | 🟢 Advanced |

---

## Pipeline Steps & File Map

| Step | File | What It Covers |
|---|---|---|
| 1 | [1-Define_the_problem.md](./1-Define_the_problem.md) | All 6 problem definitions, types, data sources |
| 2 | [2-Collect_data.md](./2-Collect_data.md) | Kaggle dataset + PostgreSQL extraction code |
| 3 | [3-Prepare_and_clean_data.md](./3-Prepare_and_clean_data.md) | Cleaning, SMOTE, encoding, per-problem prep |
| 4 | [4-Split_data.md](./4-Split_data.md) | Train/test split strategy per problem (incl. chronological for P6) |
| 5 | [5-Choose_a_model.md](./5-Choose_a_model.md) | Model candidates, comparison code, final selection |
| 6 | [6-Train_the_model.md](./6-Train_the_model.md) | `.fit()` calls, training config, what happens internally |
| 7 | [7-Evaluate_performance.md](./7-Evaluate_performance.md) | Metrics, confusion matrices, plots per problem |
| 8 | [8-Tune_and_improve.md](./8-Tune_and_improve.md) | GridSearchCV, threshold tuning, feature engineering |

---

## Final Model Decisions

| Problem | Model | Library |
|---|---|---|
| P1 — Failure Prediction | XGBoost Classifier | `xgboost` |
| P2 — Failure Type | MultiOutput Random Forest | `scikit-learn` |
| P3 — RUL Estimation | XGBoost Regressor | `xgboost` |
| P4 — Anomaly Detection | Isolation Forest | `scikit-learn` |
| P5 — Work Order Priority | XGBoost Classifier | `xgboost` |
| P6 — Scheduling | Prophet | `prophet` |

---

## Key Project Files (ML-related)

```
EAMSagemCom/
├── ML_Pipeline/                      ← You are here
│   ├── ML_PIPELINE_PLAN.md           ← This file (start here)
│   ├── 1-Define_the_problem.md
│   ├── 2-Collect_data.md
│   ├── 3-Prepare_and_clean_data.md
│   ├── 4-Split_data.md
│   ├── 5-Choose_a_model.md
│   ├── 6-Train_the_model.md
│   ├── 7-Evaluate_performance.md
│   └── 8-Tune_and_improve.md
│
├── ai4i2020.csv                      ← Training dataset (Kaggle)
├── ml_train_basic.py                 ← Training script (P1, currently)
├── ml_eda.py                         ← Exploratory data analysis
├── predict_cli.py                    ← Terminal test for P1 model
├── basic_machine_model.pkl           ← Saved P1 model (Random Forest)
│
└── app/backend/modules/ml/
    ├── ml_predictive.py              ← Active ML service (uses .pkl)
    └── router.py                     ← API: GET /api/v1/ml/machines/{id}/prediction
```

---

## How to Run

```bash
# 1. Explore the dataset
app\backend\venv\Scripts\python.exe ml_eda.py

# 2. Train P1 model
app\backend\venv\Scripts\python.exe ml_train_basic.py
# → Saves: basic_machine_model.pkl

# 3. Test a prediction
app\backend\venv\Scripts\python.exe predict_cli.py --air 301.5 --process 311.0 --rpm 1450 --torque 55.0 --wear 200
```

---

## What Remains To Be Built

- [ ] **P1** — Connect `basic_machine_model.pkl` to `ml_predictive.py` (replace hand-coded linear regression)
- [ ] **P2** — Train `MultiOutputClassifier` for failure type, expose via new API endpoint
- [ ] **P3** — Train XGBoost Regressor on `interventions` table, expose `rul_days` via API
- [ ] **P4** — Train Isolation Forest, trigger SSE alert on anomaly via `core/notifications.py`
- [ ] **P5** — Train work order priority model, integrate into `WorkOrderFormDialog.tsx`
- [ ] **P6** — Train Prophet model, visualise forecast in Planning dashboard
