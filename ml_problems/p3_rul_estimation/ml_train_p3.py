"""
P3 — RUL Estimation (Optimized)
Training script: XGBoost Regressor with GridSearchCV
Predicts Remaining Useful Life (RUL) in cycles until failure.
"""

import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import os
import time

start_time = time.time()

# ── 1. Load dataset ──────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
CSV_PATH = os.path.join(BASE_DIR, 'ai4i2020.csv')
if not os.path.exists(CSV_PATH):
    CSV_PATH = 'ai4i2020.csv'

df = pd.read_csv(CSV_PATH)
print(f"Dataset shape: {df.shape}")

# ── 2. Derive RUL ───────────────────────────────────────────────────────────
failure_indices = df.index[df['Machine failure'] == 1].tolist()

def calculate_rul(idx):
    future_failures = [f for f in failure_indices if f >= idx]
    if not future_failures:
        return 500
    return future_failures[0] - idx

print("Calculating RUL target...")
df['RUL'] = [calculate_rul(i) for i in range(len(df))]
df['RUL'] = df['RUL'].clip(upper=200)

# ── 3. Feature engineering ───────────────────────────────────────────────────
df['temp_delta'] = df['Process temperature [K]'] - df['Air temperature [K]']
df['rpm_torque'] = df['Rotational speed [rpm]'] * df['Torque [Nm]']

raw_features = [
    'Air temperature [K]', 'Process temperature [K]',
    'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]',
    'temp_delta', 'rpm_torque'
]
sanitized_features = [f.replace('[', '').replace(']', '') for f in raw_features]

X = df[raw_features].copy()
X.columns = sanitized_features
y = df['RUL']

# ── 4. Train/Test Split ──────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# ── 5. GridSearchCV ─────────────────────────────────────────────────────────
print(f"\nRunning GridSearchCV (3-fold, neg_mean_absolute_error)...")
param_grid = {
    'n_estimators': [300, 500],
    'learning_rate': [0.01, 0.05, 0.1],
    'max_depth': [4, 6, 8],
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
print("EVALUATION — P3 RUL Estimation")
print("="*60)
print(f"MAE  : {mae:.2f} cycles")
print(f"RMSE : {rmse:.2f} cycles")
print(f"R2   : {r2:.4f}")

# Feature importance
importances = best_model.feature_importances_
for feat, imp in sorted(zip(raw_features, importances), key=lambda x: -x[1]):
    print(f"  {feat:30s} {imp:.4f}")

# ── 7. Save Model ────────────────────────────────────────────────────────────
MODELS_DIR = os.path.join(BASE_DIR, 'app', 'backend', 'modules', 'ml', 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

MODEL_OUT = os.path.join(MODELS_DIR, 'ml_model_p3_rul.pkl')
if os.path.exists(MODEL_OUT):
    backup = f"{MODEL_OUT}.bak_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
    os.rename(MODEL_OUT, backup)

model_data = {
    'model': best_model,
    'features': raw_features,
    'xgb_features': sanitized_features,
    'best_params': grid.best_params_,
    'metrics': {'mae': round(mae, 2), 'rmse': round(rmse, 2), 'r2': round(r2, 4)},
}
joblib.dump(model_data, MODEL_OUT)
print(f"\nModel saved to {MODEL_OUT}")

# ── 8. Quick Tests ───────────────────────────────────────────────────────────
sample = np.array([[302.0, 312.0, 1400, 60.0, 230, 10.0, 84000.0]])
pred_rul = best_model.predict(sample)[0]
print(f"\nManual Test (High Stress): Predicted RUL = {pred_rul:.1f} cycles")

sample_healthy = np.array([[298.0, 308.0, 1550, 40.0, 10, 10.0, 62000.0]])
pred_rul_healthy = best_model.predict(sample_healthy)[0]
print(f"Manual Test (Healthy):     Predicted RUL = {pred_rul_healthy:.1f} cycles")
print(f"\n[TIME] Total training time: {time.time() - start_time:.1f}s")
