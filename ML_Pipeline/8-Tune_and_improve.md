# ML Pipeline — EAMSagemCom
## Step 8: Tune & Improve

After evaluating initial performance, this step focuses on closing the gaps identified in Step 7. Each problem has specific improvement strategies.

---

## Problem 1 — Binary Failure Prediction

### Improvement 1 — Hyperparameter Tuning with GridSearchCV

```python
from sklearn.model_selection import GridSearchCV
from xgboost import XGBClassifier

param_grid = {
    'n_estimators':  [100, 200, 300],
    'max_depth':     [4, 6, 8],
    'learning_rate': [0.05, 0.1, 0.2],
    'subsample':     [0.8, 1.0],
}

grid = GridSearchCV(
    XGBClassifier(scale_pos_weight=28, eval_metric='logloss', random_state=42),
    param_grid,
    cv=3,
    scoring='f1',
    n_jobs=-1,
    verbose=1
)
grid.fit(X_train_res, y_train_res)

print("Best params:", grid.best_params_)
print("Best F1:    ", grid.best_score_)
best_model_p1 = grid.best_estimator_
```

### Improvement 2 — Adjust Classification Threshold

By default, the model predicts "Failure" when probability > 0.5. Lowering this threshold increases recall (catching more real failures at the cost of more false alarms):

```python
import numpy as np

y_proba = best_model_p1.predict_proba(X_test)[:, 1]

# Try different thresholds and compare recall
for threshold in [0.3, 0.4, 0.5]:
    y_pred_thresh = (y_proba >= threshold).astype(int)
    from sklearn.metrics import recall_score, precision_score
    rec = recall_score(y_test, y_pred_thresh)
    pre = precision_score(y_test, y_pred_thresh)
    print(f"Threshold {threshold}: Recall={rec:.2f}  Precision={pre:.2f}")
```

### Improvement 3 — Switch Balancing Strategy

```python
# Option A: SMOTE (current)
from imblearn.over_sampling import SMOTE
smote = SMOTE(random_state=42)

# Option B: ADASYN (generates samples in harder regions)
from imblearn.over_sampling import ADASYN
adasyn = ADASYN(random_state=42)

# Option C: Undersampling (remove majority class samples)
from imblearn.under_sampling import RandomUnderSampler
rus = RandomUnderSampler(random_state=42)
```

---

## Problem 2 — Failure Type Classification

### Improvement — Per-label Tuning

Some failure types (like `RNF` — Random Failure) are nearly impossible to predict. Focus tuning effort on labels with actual signal:

```python
# Focus on HDF — highest correlation with failure
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV

param_grid = {'n_estimators': [100, 200], 'max_depth': [None, 10, 20]}
grid_hdf = GridSearchCV(
    RandomForestClassifier(class_weight='balanced', random_state=42),
    param_grid, cv=3, scoring='f1', n_jobs=-1
)
grid_hdf.fit(X_train_p2, y_train_p2['HDF'])
print("Best HDF model:", grid_hdf.best_params_)
```

### Improvement — Add Feature: Temperature Delta

From the dataset, HDF is driven by the **difference** between Process Temp and Air Temp:

```python
# Engineer a new feature
X_p2_eng = X_p2.copy()
X_p2_eng['temp_delta'] = X_p2_eng['Process temperature [K]'] - X_p2_eng['Air temperature [K]']
# This should improve HDF recall significantly
```

---

## Problem 3 — RUL Estimation

### Improvement — Add More Features from DB

If RMSE is too high, enrich the feature set with more context from the database:

```python
# Add: number of past interventions, machine age, work order count
X_rul_v2 = df_int[['days_since_last', 'duration', 'intervention_count', 'machine_age_days']]
```

### Improvement — Try Gradient Boosting Variants

```python
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import cross_val_score
import numpy as np

model_gbr = GradientBoostingRegressor(n_estimators=200, max_depth=4, random_state=42)
scores = cross_val_score(model_gbr, X_train_r, y_train_r, cv=5, scoring='neg_mean_squared_error')
rmse_cv = np.sqrt(-scores.mean())
print(f"GBR CV RMSE: {rmse_cv:.2f} days")
```

---

## Problem 4 — Anomaly Detection

### Improvement — Tune Contamination Parameter

```python
from sklearn.ensemble import IsolationForest
from sklearn.metrics import f1_score

# Try different contamination values
for cont in [0.01, 0.034, 0.05, 0.10]:
    model = IsolationForest(n_estimators=100, contamination=cont, random_state=42)
    model.fit(X_train_ad)
    preds = (model.predict(X_score_ad) == -1).astype(int)
    f1 = f1_score(y_true_ad, preds)
    print(f"contamination={cont}: F1={f1:.4f}")
```

### Improvement — Switch to Local Outlier Factor

```python
from sklearn.neighbors import LocalOutlierFactor

lof = LocalOutlierFactor(n_neighbors=20, contamination=0.034, novelty=True)
lof.fit(X_train_ad)
preds_lof = (lof.predict(X_score_ad) == -1).astype(int)
```

---

## Problem 5 — Work Order Priority

### Improvement — Feature Engineering

Add more meaningful features derived from real EAM data:

```python
# Time since last intervention (urgency signal)
df_wo['days_since_last'] = (pd.Timestamp.now() - pd.to_datetime(df_wo['last_intervention'])).dt.days

# Rolling failure rate per machine type
df_wo['failure_rate'] = df_wo.groupby('machine_type')['had_failure'].transform('mean')

# Re-train with enriched features
X_wo_v2 = df_wo[['machine_type_enc', 'intervention_count', 'days_since_last', 'failure_rate']]
```

### Improvement — Handle Class Imbalance (CRITICAL is rare)

```python
from xgboost import XGBClassifier

# Use sample_weight to make rare priorities (CRITICAL) count more
sample_weights = y_train_wo.map({0: 1, 1: 1, 2: 3, 3: 5})  # Weight CRITICAL 5×

model_p5_v2 = XGBClassifier(objective='multi:softmax', num_class=4, random_state=42)
model_p5_v2.fit(X_train_wo, y_train_wo, sample_weight=sample_weights)
```

---

## Problem 6 — Maintenance Scheduling

### Improvement — Add Machine-Specific Regressors

Prophet's default model is global. Add machine-specific context as regressors:

```python
model_p6_v2 = Prophet(yearly_seasonality=True)
model_p6_v2.add_regressor('zone_encoded')   # Zone affects wear rate
model_p6_v2.add_regressor('machine_age')    # Older machines need more frequent maintenance
model_p6_v2.fit(df_prophet_v2)
```

---

## General Improvement Strategies

| Strategy | When to Use | Tools |
|---|---|---|
| **GridSearchCV** | Too many hyperparameters to tune manually | `sklearn.model_selection` |
| **Lower threshold** | Recall too low on failure class | `predict_proba()` |
| **SMOTE / ADASYN** | Class imbalance causing poor minority recall | `imbalanced-learn` |
| **Feature engineering** | Model plateaus — add domain knowledge | `pandas` |
| **Cross-validation** | Small dataset — want stable estimates | `cross_val_score()` |
| **Early stopping** (XGBoost) | Overfitting on training data | `eval_set`, `early_stopping_rounds` |

### XGBoost Early Stopping Example

```python
model_p1_es = XGBClassifier(n_estimators=500, learning_rate=0.05,
                              scale_pos_weight=28, random_state=42)

model_p1_es.fit(
    X_train_res, y_train_res,
    eval_set=[(X_test, y_test)],
    early_stopping_rounds=20,   # Stop if no improvement after 20 rounds
    verbose=50
)
print("Best iteration:", model_p1_es.best_iteration)
```

---

## Tuning Summary

| Problem | Main Improvement | Expected Gain |
|---|---|---|
| P1 — Failure Prediction | Lower threshold to 0.35–0.4 | Recall ↑ from 63% → 85%+ |
| P2 — Failure Type | Add `temp_delta` feature | HDF recall ↑ |
| P3 — RUL Estimation | Add machine age + intervention count features | RMSE ↓ |
| P4 — Anomaly Detection | Tune `contamination` parameter | Better precision-recall tradeoff |
| P5 — Work Order Priority | Weight CRITICAL class 5× | CRITICAL recall ↑ |
| P6 — Scheduling | Add zone & machine age regressors | MAE ↓ |
