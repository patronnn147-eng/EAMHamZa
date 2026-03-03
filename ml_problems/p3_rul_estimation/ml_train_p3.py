"""
P3 — RUL Estimation
Training script: XGBoost Regressor predicting
Remaining Useful Life (RUL) in cycles/rows until failure.

Strategy:
- Derive RUL by calculating distance to the next 'Machine failure == 1'.
- Use telemetry features as input.
"""

import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import os

# ── 1. Load dataset ──────────────────────────────────────────────────────────
# Find project root (3 levels up from this script in ml_problems/p3_rul_estimation/)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR)))
CSV_PATH = os.path.join(BASE_DIR, 'ai4i2020.csv')

if not os.path.exists(CSV_PATH):
    # Fallback to current working directory if not found in project structure
    CSV_PATH = 'ai4i2020.csv'

df = pd.read_csv(CSV_PATH)
print(f"Dataset shape: {df.shape}")

# ── 2. Derive RUL (Remaining Useful Life) ───────────────────────────────────
# Calculate indices of failures
failure_indices = df.index[df['Machine failure'] == 1].tolist()

def calculate_rul(idx):
    # Find the first failure index that is >= current index
    future_failures = [f for f in failure_indices if f >= idx]
    if not future_failures:
        return 500 # Cap RUL at 500 if no failure in sight
    return future_failures[0] - idx

print("Calculating RUL target...")
df['RUL'] = [calculate_rul(i) for i in range(len(df))]
df['RUL'] = df['RUL'].clip(upper=200)

# ── 3. Feature Selection ─────────────────────────────────────────────────────
raw_features = [
    'Air temperature [K]',
    'Process temperature [K]',
    'Rotational speed [rpm]',
    'Torque [Nm]',
    'Tool wear [min]'
]

# XGBoost doesn't like brackets [] in feature names
sanitized_features = [f.replace('[', '').replace(']', '') for f in raw_features]

X = df[raw_features].copy()
X.columns = sanitized_features 
y = df['RUL']

# ── 4. Train/Test Split ──────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# ── 5. Train XGBoost Regressor ──────────────────────────────────────────────
print(f"Training XGBoost Regressor on {len(sanitized_features)} features...")
model_p3 = XGBRegressor(
    n_estimators=500,
    learning_rate=0.05,
    max_depth=6,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1
)

model_p3.fit(X_train, y_train)
print("Training complete.")

# ── 6. Evaluate ──────────────────────────────────────────────────────────────
y_pred = model_p3.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)

print("\n" + "="*60)
print("EVALUATION — Regression Metrics")
print("="*60)
print(f"MAE  : {mae:.2f} cycles")
print(f"RMSE : {rmse:.2f} cycles")
print(f"R2   : {r2:.4f}")

# ── 7. Save Model ────────────────────────────────────────────────────────────
MODELS_DIR = os.path.join(BASE_DIR, 'app', 'backend', 'modules', 'ml', 'models')
if not os.path.exists(MODELS_DIR):
    os.makedirs(MODELS_DIR, exist_ok=True)

MODEL_OUT = os.path.join(MODELS_DIR, 'ml_model_p3_rul.pkl')
joblib.dump(model_p3, MODEL_OUT)
print(f"\nModel saved to {MODEL_OUT}")

# ── 8. Quick Manual Test ─────────────────────────────────────────────────────
sample = np.array([[302.0, 312.0, 1400, 60.0, 230]]) 
pred_rul = model_p3.predict(sample)[0]
print(f"\nManual Test (High Stress): Predicted RUL = {pred_rul:.1f} cycles")

sample_healthy = np.array([[298.0, 308.0, 1550, 40.0, 10]])
pred_rul_healthy = model_p3.predict(sample_healthy)[0]
print(f"Manual Test (Healthy):     Predicted RUL = {pred_rul_healthy:.1f} cycles")
