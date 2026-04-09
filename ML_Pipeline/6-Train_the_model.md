# ML Pipeline — EAMSagemCom
## Step 6: Train the Model

Each model is trained on the prepared, balanced training data from Step 4. This step covers the actual `.fit()` calls, training configuration, and what happens internally.

---

## Problem 1 — Binary Failure Prediction (XGBoost)

```python
from xgboost import XGBClassifier
from sklearn.model_selection import GridSearchCV

# Define model
model_p1 = XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    scale_pos_weight=28,   # 9661 / 339 ≈ 28 (handles imbalance)
    eval_metric='logloss',
    random_state=42
)

# Optional: Tune with GridSearchCV
param_grid = {
    'n_estimators': [100, 200, 300],
    'max_depth': [4, 6, 8],
    'learning_rate': [0.05, 0.1, 0.2]
}

grid = GridSearchCV(model_p1, param_grid, cv=3, scoring='f1', n_jobs=-1, verbose=1)
grid.fit(X_train_res, y_train_res)

best_model_p1 = grid.best_estimator_
print("Best params:", grid.best_params_)
```

**What happens during training:**
- XGBoost builds trees **sequentially** — each tree corrects the errors of the previous one
- `scale_pos_weight=28` tells the model to penalise missing a failure 28× more than a false alarm
- `cv=3` runs 3-fold cross-validation to find the best hyperparameters

---

## Problem 2 — Failure Type Classification (MultiOutput Random Forest)

```python
from sklearn.multioutput import MultiOutputClassifier
from sklearn.ensemble import RandomForestClassifier

model_p2 = MultiOutputClassifier(
    RandomForestClassifier(
        n_estimators=200,
        class_weight='balanced',
        random_state=42
    )
)

# y_train_p2 has 5 columns: TWF, HDF, PWF, OSF, RNF
model_p2.fit(X_train_p2, y_train_p2)
print("Training complete — 5 independent classifiers fitted")
```

**What happens during training:**
- `MultiOutputClassifier` fits **one Random Forest per label** (5 models total)
- Each tree votes on whether TWF/HDF/PWF/OSF/RNF is present
- `class_weight='balanced'` automatically adjusts for imbalance per label

---

## Problem 3 — RUL Estimation (XGBoost Regressor)

```python
from xgboost import XGBRegressor

model_p3 = XGBRegressor(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    random_state=42
)

model_p3.fit(X_train_r, y_train_r)
print("RUL model trained")
```

**What happens during training:**
- XGBoost minimises **RMSE** (Root Mean Squared Error) to predict `rul_days`
- Each boosting round reduces prediction error on the training set
- Trees are built on the residuals of the previous prediction

---

## Problem 4 — Anomaly Detection (Isolation Forest)

```python
from sklearn.ensemble import IsolationForest

model_p4 = IsolationForest(
    n_estimators=100,
    contamination=0.034,   # Expected % of anomalies (3.4% from dataset)
    random_state=42
)

# Train ONLY on healthy machines
model_p4.fit(X_train_ad)
print("Anomaly detector trained on normal machine data")
```

**What happens during training:**
- Isolation Forest builds **random trees** that try to isolate data points
- Anomalies (failures) are isolated in **fewer splits** — they are statistically "easier to isolate"
- `contamination=0.034` sets the threshold for flagging anomalies
- **No labels used** — purely unsupervised

---

## Problem 5 — Work Order Priority Prediction (XGBoost Multi-class)

```python
from xgboost import XGBClassifier

model_p5 = XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    num_class=4,            # LOW, MEDIUM, HIGH, CRITICAL
    objective='multi:softmax',
    eval_metric='mlogloss',
    random_state=42
)

model_p5.fit(X_train_wo, y_train_wo)
print("Work order priority model trained")
```

**What happens during training:**
- XGBoost uses **softmax** to output probabilities for each of the 4 priority classes
- `mlogloss` (multi-class log loss) is minimised during training
- The model learns which features (machine age, intervention count, days since last) best predict urgency

---

## Problem 6 — Maintenance Scheduling (Prophet)

```python
from prophet import Prophet

# Prophet requires columns: 'ds' (date) and 'y' (value to forecast)
df_prophet = df_train_ts.rename(columns={'date': 'ds', 'days_between': 'y'})

model_p6 = Prophet(
    yearly_seasonality=True,
    weekly_seasonality=False,
    daily_seasonality=False,
    interval_width=0.95     # 95% confidence interval
)

model_p6.fit(df_prophet)
print("Maintenance schedule model trained")
```

**What happens during training:**
- Prophet decomposes the time-series into **trend + seasonality + holidays**
- Finds patterns like "machines in Zone A tend to need maintenance every ~30 days"
- `yearly_seasonality=True` captures seasonal wear patterns (e.g. higher failure rate in summer due to heat)

---

## Training Summary

| Problem | Model | Training Data | Key Config |
|---|---|---|---|
| P1 — Failure Prediction | XGBoost Classifier | X_train_res (balanced) | `scale_pos_weight=28`, GridSearchCV |
| P2 — Failure Type | MultiOutput RF | X_train_p2 | 5 classifiers, `class_weight='balanced'` |
| P3 — RUL Estimation | XGBoost Regressor | X_train_r | Minimise RMSE |
| P4 — Anomaly Detection | Isolation Forest | X_train_ad (healthy only) | `contamination=0.034` |
| P5 — Work Order Priority | XGBoost Multi-class | X_train_wo | `objective='multi:softmax'` |
| P6 — Scheduling | Prophet | df_train_ts (chronological) | `yearly_seasonality=True` |

---

## Run Training from Terminal

```bash
# From project root
app\backend\venv\Scripts\python.exe ml_train_basic.py
# → Trains P1 model and saves basic_machine_model.pkl
```

> Each problem can be extracted into its own training script (e.g. `ml_train_p2.py`, `ml_train_p3.py`) as the project grows.
