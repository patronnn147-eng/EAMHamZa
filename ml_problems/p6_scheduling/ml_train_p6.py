"""
P6 — Maintenance Schedule Optimization (Optimized)
Training script: XGBoost Regressor with GridSearchCV
"""

import pandas as pd
import numpy as np
import os
import joblib
import time
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split, GridSearchCV
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

# ── 4. Train/Test Split ──────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# ── 5. GridSearchCV ─────────────────────────────────────────────────────────
print("\nRunning GridSearchCV (3-fold, neg_mean_absolute_error)...")
param_grid = {
    'n_estimators': [200, 500],
    'max_depth': [6, 10, 15],
    'learning_rate': [0.05, 0.1],
}

grid = GridSearchCV(
    estimator=XGBRegressor(
        subsample=0.8, colsample_bytree=0.8,
        random_state=42, n_jobs=-1, tree_method='hist',
    ),
    param_grid=param_grid,
    cv=3,
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
    'metrics': {'mae': round(mae, 2), 'rmse': round(rmse, 2), 'r2': round(r2, 4)},
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
