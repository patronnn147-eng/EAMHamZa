"""
P6 — Maintenance Schedule Optimization (Optimized)
Training script: XGBoost Regressor with GridSearchCV + TimeSeriesSplit(5)

Improvements:
- TimeSeriesSplit(5) instead of cv=3 — preserves temporal order, prevents leakage
- Standalone cross_val_score: neg_MAE, R²
"""

import pandas as pd
import numpy as np
import os
import joblib
import time
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split, GridSearchCV, TimeSeriesSplit, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

start_time = time.time()

# ── 1. Load dataset ──────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
CSV_PATH = os.path.join(BASE_DIR, 'ai4i2020.csv')
if not os.path.exists(CSV_PATH):
    CSV_PATH = 'ai4i2020.csv'

df = pd.read_csv(CSV_PATH)
print(f"Dataset Loaded: {df.shape}")

# ── 2. Derive Ground Truth: Optimal Days to Maintenance ─────────────────────
failure_indices = df.index[df['Machine failure'] == 1].tolist()

def get_dist_to_failure(idx):
    future_failures = [f for f in failure_indices if f >= idx]
    if not future_failures:
        return 500
    return future_failures[0] - idx

print("Calculating distance to next failure for each sample...")
df['dist_to_failure'] = [get_dist_to_failure(i) for i in range(len(df))]

def calc_maintenance_days(row):
    dist = row['dist_to_failure']
    failure = row['Machine failure']
    if failure == 1:
        return 0
    elif dist <= 5:
        return max(1, dist * 0.2)
    elif dist <= 30:
        return 1 + (dist - 5) * 0.24
    elif dist <= 100:
        return 7 + (dist - 30) * 0.1
    else:
        return min(30, 14 + (dist - 100) * 0.04)

df['maintenance_days'] = df.apply(calc_maintenance_days, axis=1)
print("\nMaintenance Days Distribution:")
print(df['maintenance_days'].describe())

# ── 3. Feature engineering ───────────────────────────────────────────────────
df['temp_delta'] = df['Process temperature [K]'] - df['Air temperature [K]']
df['rpm_torque'] = df['Rotational speed [rpm]'] * df['Torque [Nm]']
df['tool_wear_sq'] = df['Tool wear [min]'] ** 2

raw_features = [
    'Air temperature [K]', 'Process temperature [K]',
    'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]',
    'temp_delta', 'rpm_torque', 'tool_wear_sq'
]
sanitized_features = [f.replace('[', '').replace(']', '') for f in raw_features]

X = df[raw_features].copy()
X.columns = sanitized_features
y = df['maintenance_days']

# ── 4. Train/Test Split (temporal) ──────────────────────────────────────────
# Temporal split: last 20% = test (preserves time order, no shuffling)
split_idx = int(len(X) * 0.8)
X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
print(f"\nTemporal split: train={len(X_train)}, test={len(X_test)}")

# ── 5. GridSearchCV with TimeSeriesSplit ─────────────────────────────────────
# TimeSeriesSplit preserves temporal order — no future days leak into training folds
print("\nRunning GridSearchCV (TimeSeriesSplit(5), neg_mean_absolute_error)...")
param_grid = {
    'n_estimators': [200, 500],
    'max_depth': [6, 10, 15],
    'learning_rate': [0.05, 0.1],
}

tscv = TimeSeriesSplit(n_splits=5)

grid = GridSearchCV(
    estimator=XGBRegressor(
        subsample=0.8, colsample_bytree=0.8,
        random_state=42, n_jobs=-1, tree_method='hist',
    ),
    param_grid=param_grid,
    cv=tscv,
    scoring='neg_mean_absolute_error',
    n_jobs=-1,
    verbose=1,
)
grid.fit(X_train, y_train)

best_model = grid.best_estimator_
print(f"\n[TIME] GridSearchCV took: {time.time() - start_time:.1f}s")
print("\n[OK] Best hyper-parameters:")
for k, v in grid.best_params_.items():
    print(f"  {k}: {v}")

# ── 6. Evaluate ──────────────────────────────────────────────────────────────
y_pred = best_model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)

print("\n" + "="*60)
print("EVALUATION — P6 Maintenance Schedule Regression")
print("="*60)
print(f"MAE  (Mean Absolute Error):  {mae:.2f} days")
print(f"RMSE (Root Mean Sq Error):   {rmse:.2f} days")
print(f"R2   (Coefficient of Det):   {r2:.4f}")

# ── 6b. Standalone Cross-Validation (TimeSeriesSplit — temporal safe) ─────────
# cross_val_score clones best_model — model untouched.
print("\n" + "="*60)
print("CROSS-VALIDATION — P6 Schedule Optimization (TimeSeriesSplit(5))")
print("="*60)

cv_tscv = TimeSeriesSplit(n_splits=5)

print("Running CV (neg_MAE)...")
cv_mae = cross_val_score(best_model, X, y, cv=cv_tscv, scoring='neg_mean_absolute_error', n_jobs=-1)
print("Running CV (R²)...")
cv_r2 = cross_val_score(best_model, X, y, cv=cv_tscv, scoring='r2', n_jobs=-1)

print(f"\nMAE  : {-cv_mae.mean():.2f} ± {cv_mae.std():.2f} days  folds={(-cv_mae).round(2).tolist()}")
print(f"R²   : {cv_r2.mean():.4f} ± {cv_r2.std():.4f}         folds={cv_r2.round(4).tolist()}")

# ── 7. Save Model ────────────────────────────────────────────────────────────
MODELS_DIR = os.path.join(BASE_DIR, 'app', 'backend', 'modules', 'ml', 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

MODEL_OUT = os.path.join(MODELS_DIR, 'ml_model_p6_schedule.pkl')
if os.path.exists(MODEL_OUT):
    backup = f"{MODEL_OUT}.bak_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
    os.rename(MODEL_OUT, backup)

joblib.dump({
    'model': best_model,
    'features': raw_features,
    'xgb_features': sanitized_features,
    'best_params': grid.best_params_,
    'metrics': {
        'mae':  round(mae, 2),
        'rmse': round(rmse, 2),
        'r2':   round(r2, 4),
        'cv': {
            'mae_mean': round(float(-cv_mae.mean()), 2),
            'mae_std':  round(float(cv_mae.std()),   2),
            'r2_mean':  round(float(cv_r2.mean()),   4),
            'r2_std':   round(float(cv_r2.std()),    4),
        }
    },
}, MODEL_OUT)
print(f"\nModel saved to {MODEL_OUT}")

# ── 8. Quick Tests ───────────────────────────────────────────────────────────
print("\n--- Quick Verification ---")
sample_critical = np.array([[303.0, 313.0, 1300, 65.0, 240, 10.0, 84500.0, 57600.0]])
pred_crit = best_model.predict(sample_critical)[0]
print(f"Critical Machine  -> Schedule in: {pred_crit:.1f} days")

sample_healthy = np.array([[298.0, 308.0, 1550, 38.0, 15, 10.0, 58900.0, 225.0]])
pred_healthy = best_model.predict(sample_healthy)[0]
print(f"Healthy Machine   -> Schedule in: {pred_healthy:.1f} days")

sample_medium = np.array([[300.0, 310.0, 1400, 50.0, 120, 10.0, 70000.0, 14400.0]])
pred_medium = best_model.predict(sample_medium)[0]
print(f"Medium Stress     -> Schedule in: {pred_medium:.1f} days")
print(f"\n[TIME] Total training time: {time.time() - start_time:.1f}s")
