# ML Pipeline — EAMSagemCom
## Step 5: Choose a Model

A different model is chosen for each of the 6 ML problems based on the problem type, data size, and interpretability requirements.

---

## Problem 1 — Binary Failure Prediction

We compare 4 candidate models and pick the one with the best F1 score.

### 🌲 Model A — Random Forest *(Current Choice)*
```python
from sklearn.ensemble import RandomForestClassifier
model_rf = RandomForestClassifier(
    n_estimators=200, max_depth=None, class_weight='balanced', random_state=42
)
```

### ⚡ Model B — XGBoost *(Strong Challenger)*
```python
from xgboost import XGBClassifier
model_xgb = XGBClassifier(
    n_estimators=200, max_depth=6, learning_rate=0.1,
    scale_pos_weight=28,  # negatives/positives ratio
    eval_metric='logloss', random_state=42
)
```

### 📈 Model C — Logistic Regression *(Baseline)*
```python
from sklearn.linear_model import LogisticRegression
model_lr = LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42)
```

### 🧠 Model D — MLP Neural Network *(Advanced)*
```python
from sklearn.neural_network import MLPClassifier
model_mlp = MLPClassifier(hidden_layer_sizes=(64, 32), activation='relu', max_iter=300, random_state=42)
```

### Run All & Compare
```python
from sklearn.metrics import f1_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

models = {
    "Random Forest":       model_rf,
    "XGBoost":             model_xgb,
    "Logistic Regression": Pipeline([('sc', StandardScaler()), ('clf', model_lr)]),
    "MLP Neural Net":      Pipeline([('sc', StandardScaler()), ('clf', model_mlp)]),
}

for name, model in models.items():
    model.fit(X_train_res, y_train_res)
    f1 = f1_score(y_test, model.predict(X_test))
    print(f"{name:25s} → F1: {f1:.4f}")
```

| Model | Pros | Cons |
|---|---|---|
| Random Forest | Robust, no scaling needed, interpretable | Large .pkl |
| XGBoost | Best F1 on tabular imbalanced data | More hyperparams |
| Logistic Regression | Fast, very interpretable | Assumes linearity |
| MLP Neural Net | Learns complex patterns | Black box, needs scaling |

**→ Winner: XGBoost** (best F1 on imbalanced sensor data)

---

## Problem 2 — Failure Type Classification (Multi-label)

```python
from sklearn.multioutput import MultiOutputClassifier
from sklearn.ensemble import RandomForestClassifier

model_p2 = MultiOutputClassifier(
    RandomForestClassifier(n_estimators=200, class_weight='balanced', random_state=42)
)
# Fits one RF per label: TWF, HDF, PWF, OSF, RNF
model_p2.fit(X_train_p2, y_train_p2)
```

**→ Choice: MultiOutput Random Forest** — simple, interpretable, works well per label.

---

## Problem 3 — RUL Estimation (Regression)

Two candidates:

```python
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor

model_rul_rf  = RandomForestRegressor(n_estimators=200, random_state=42)
model_rul_xgb = XGBRegressor(n_estimators=200, learning_rate=0.1, random_state=42)
```

Evaluate with RMSE:
```python
from sklearn.metrics import mean_squared_error
import numpy as np

for name, model in [("RF Regressor", model_rul_rf), ("XGB Regressor", model_rul_xgb)]:
    model.fit(X_train_r, y_train_r)
    rmse = np.sqrt(mean_squared_error(y_test_r, model.predict(X_test_r)))
    print(f"{name}: RMSE = {rmse:.2f} days")
```

**→ Winner: XGBoost Regressor** (typically lower RMSE on tabular data)

---

## Problem 4 — Anomaly Detection (Unsupervised)

No labels required. The model learns the distribution of healthy machines and flags deviations.

```python
from sklearn.ensemble import IsolationForest

model_ad = IsolationForest(
    n_estimators=100,
    contamination=0.034,  # Estimated % of anomalies (~3.4% from dataset)
    random_state=42
)
model_ad.fit(X_train_ad)  # Train on healthy machines only

# Score = -1 (anomaly) or +1 (normal)
scores = model_ad.predict(X_score_ad)
```

**→ Choice: Isolation Forest** — fast, no labels needed, interprets well for EAM alerts.

---

## Problem 5 — Work Order Priority Prediction

Multi-class classification (LOW / MEDIUM / HIGH / CRITICAL):

```python
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

model_wo_rf  = RandomForestClassifier(n_estimators=200, class_weight='balanced', random_state=42)
model_wo_xgb = XGBClassifier(n_estimators=200, eval_metric='mlogloss', random_state=42)
```

Evaluate with macro F1 (treats all 4 classes equally):
```python
from sklearn.metrics import f1_score
f1 = f1_score(y_test_wo, model.predict(X_test_wo), average='macro')
```

**→ Winner: XGBoost** (handles multi-class well with `eval_metric='mlogloss'`)

---

## Problem 6 — Maintenance Schedule Optimization (Time-Series)

Forecasting the next best maintenance date per machine:

```python
# Option A — Facebook Prophet (simple, interpretable)
from prophet import Prophet
model_prophet = Prophet(yearly_seasonality=True, weekly_seasonality=False)
model_prophet.fit(df_train_ts.rename(columns={'date': 'ds', 'days_between': 'y'}))

# Option B — ARIMA (classic time-series)
from statsmodels.tsa.arima.model import ARIMA
model_arima = ARIMA(y_train_ts, order=(1, 1, 1))
model_arima_fit = model_arima.fit()
```

**→ Choice: Prophet** — easier to use, handles seasonality automatically, good for academic demo.

---

## Final Model Selection Summary

| Problem | Chosen Model | Type | Library |
|---|---|---|---|
| P1 — Failure Prediction | **XGBoost Classifier** | Classification | `xgboost` |
| P2 — Failure Type | **MultiOutput Random Forest** | Multi-label | `scikit-learn` |
| P3 — RUL Estimation | **XGBoost Regressor** | Regression | `xgboost` |
| P4 — Anomaly Detection | **Isolation Forest** | Unsupervised | `scikit-learn` |
| P5 — Work Order Priority | **XGBoost Classifier** | Multi-class | `xgboost` |
| P6 — Scheduling | **Prophet** | Time-series | `prophet` |
