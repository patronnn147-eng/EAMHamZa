# ML Pipeline — EAMSagemCom
## Step 1: Define the Problem

This EAM (Enterprise Asset Management) platform for **Sagemcom** manages machines, work orders, technicians, and maintenance plannings. Below are all the ML problems that can be applied to this project.

---

## Problem 1 — Predictive Maintenance ✅ (In Progress)

> *"Will this machine fail soon?"*

**Type:** Binary Classification (0 = Healthy, 1 = Failed)

| Pipeline Step | What We Do |
|---|---|
| **Define the problem** | Predict if a machine will fail based on sensor telemetry |
| **Collect data** | `ai4i2020.csv` — 10,000 rows (Kaggle AI4I 2020 dataset) |
| **Prepare & clean** | Select 5 features: Air Temp, Process Temp, RPM, Torque, Tool Wear |
| **Split data** | 80/20 train-test split with `stratify=y` |
| **Choose a model** | `RandomForestClassifier` (handles non-linear sensor data) |
| **Train the model** | `ml_train_basic.py` with SMOTE oversampling + GridSearchCV tuning |
| **Evaluate** | Confusion matrix — 98% accuracy, 63% recall on failures |
| **Tune & improve** | `class_weight='balanced'`, SMOTE, GridSearchCV — done |
| **Save the model** | `basic_machine_model.pkl` |
| **Deploy** | `GET /api/v1/ml/machines/{id}/prediction` → displayed in `PredictivePanel.tsx` |

---

## Problem 2 — Failure Type Classification

> *"What TYPE of failure is likely?"*

**Type:** Multi-label Classification

Your dataset includes 5 failure sub-labels:
- `TWF` — Tool Wear Failure
- `HDF` — Heat Dissipation Failure (**57% correlation** with failure — strongest predictor)
- `PWF` — Power Failure
- `OSF` — Overstrain Failure
- `RNF` — Random Failure

**Benefit for EAM:** Auto-suggest work order type (mechanical, electrical, thermal) so the ChefTech assigns the right technician.

---

## Problem 3 — Remaining Useful Life (RUL) Estimation

> *"How many days before this machine needs maintenance?"*

**Type:** Regression (`RandomForestRegressor` or XGBoost)

- **Input:** Tool wear progression over time + intervention history
- **Output:** `rul_days` ← already displayed in `PredictivePanel.tsx`
- **Data source:** Real operational data from your PostgreSQL `interventions` table

> ⚠️ The current `ml_predictive.py` uses a hand-coded linear regression. This should be replaced with a trained regression model.

---

## Problem 4 — Anomaly Detection

> *"Is this machine behaving abnormally right now?"*

**Type:** Unsupervised Learning (no labels needed)

- **Model:** Isolation Forest or Autoencoder
- **Input:** Real-time telemetry (temperature, RPM, torque)
- **Benefit for EAM:** Trigger SSE alerts via `core/notifications.py` when anomaly is detected — even before a failure is predicted
- **Data source:** `ai4i2020.csv` for training, then applied on live machine data

---

## Problem 5 — Work Order Priority Prediction

> *"How urgent should this work order be?"*

**Type:** Multi-class Classification

- **Classes:** `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
- **Features:** Machine age, time since last maintenance, number of previous interventions, machine zone
- **Data source:** Your own PostgreSQL `work_orders` and `interventions` tables
- **Benefit for EAM:** ChefTech gets auto-suggested priorities when creating work orders

---

## Problem 6 — Maintenance Schedule Optimization *(Advanced)*

> *"When is the BEST time to schedule maintenance for all machines?"*

**Type:** Time-series Forecasting (ARIMA, Prophet, or LSTM)

- **Input:** Historical planning data + failure rates per machine
- **Benefit for EAM:** Fewer unexpected breakdowns, better technician allocation across zones (Sub-Zone, Order)

---

## Summary

| # | Problem | ML Type | Priority | Data Source |
|---|---|---|---|---|
| 1 | Binary failure prediction | Classification | ✅ Done | `ai4i2020.csv` |
| 2 | Failure type (TWF/HDF/PWF…) | Multi-label | 🔴 High | `ai4i2020.csv` |
| 3 | RUL estimation | Regression | 🔴 High | PostgreSQL DB + Kaggle |
| 4 | Anomaly detection | Unsupervised | 🟡 Medium | Sensor telemetry |
| 5 | Work order priority | Classification | 🟡 Medium | PostgreSQL DB |
| 6 | Maintenance scheduling | Time-series | 🟢 Advanced | Planning history |

---
