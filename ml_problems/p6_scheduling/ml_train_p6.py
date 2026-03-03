"""
P6 — Maintenance Schedule Optimization
Training script: Regression model predicting the optimal number of days
until maintenance should be scheduled.

Strategy:
- Derive a "days_to_maintenance" target from dist_to_failure and failure status.
- Features: Air temp, Process temp, RPM, Torque, Tool wear.
- Model: Random Forest Regressor → outputs a continuous value (days).
"""

import pandas as pd
import numpy as np
import os
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# ── 1. Load dataset ──────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
CSV_PATH = os.path.join(BASE_DIR, 'ai4i2020.csv')

if not os.path.exists(CSV_PATH):
    CSV_PATH = 'ai4i2020.csv'

df = pd.read_csv(CSV_PATH)
print(f"Dataset Loaded: {df.shape}")

# ── 2. Derive Ground Truth: Optimal Days to Maintenance ─────────────────────
# For each sample, calculate how far away it is from the next failure event.
# This represents the "ideal" maintenance window — schedule before failure.
failure_indices = df.index[df['Machine failure'] == 1].tolist()

def get_dist_to_failure(idx):
    """Distance (in samples/cycles) to the next failure event."""
    future_failures = [f for f in failure_indices if f >= idx]
    if not future_failures:
        return 500  # Far from any failure — low urgency
    return future_failures[0] - idx

print("Calculating distance to next failure for each sample...")
df['dist_to_failure'] = [get_dist_to_failure(i) for i in range(len(df))]

# Convert to "recommended days to schedule maintenance"
# Logic:
#   - If machine is about to fail (dist <= 5):  schedule in 0-1 days (IMMEDIATE)
#   - If approaching failure (dist <= 30):       schedule in 1-7 days
#   - If moderate distance (dist <= 100):        schedule in 7-14 days
#   - If far from failure (dist > 100):          schedule in 14-30 days
def calc_maintenance_days(row):
    dist = row['dist_to_failure']
    failure = row['Machine failure']
    
    if failure == 1:
        return 0  # Already failing — immediate maintenance
    elif dist <= 5:
        return max(1, dist * 0.2)  # 0-1 days
    elif dist <= 30:
        return 1 + (dist - 5) * 0.24  # 1-7 days
    elif dist <= 100:
        return 7 + (dist - 30) * 0.1  # 7-14 days
    else:
        return min(30, 14 + (dist - 100) * 0.04)  # 14-30 days (capped)

df['maintenance_days'] = df.apply(calc_maintenance_days, axis=1)

print("\nMaintenance Days Distribution:")
print(df['maintenance_days'].describe())

# ── 3. Feature Selection ─────────────────────────────────────────────────────
features = [
    'Air temperature [K]',
    'Process temperature [K]',
    'Rotational speed [rpm]',
    'Torque [Nm]',
    'Tool wear [min]'
]

X = df[features]
y = df['maintenance_days']

# ── 4. Train/Test Split ──────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# ── 5. Train Random Forest Regressor ─────────────────────────────────────────
print("\nTraining Maintenance Schedule Regressor (Random Forest)...")
model_p6 = RandomForestRegressor(
    n_estimators=200,
    max_depth=15,
    min_samples_split=5,
    random_state=42,
    n_jobs=-1
)

model_p6.fit(X_train, y_train)
print("Training complete.")

# ── 6. Evaluate ──────────────────────────────────────────────────────────────
y_pred = model_p6.predict(X_test)

mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)

print("\n" + "="*60)
print("EVALUATION — Maintenance Schedule Regression")
print("="*60)
print(f"MAE  (Mean Absolute Error):  {mae:.2f} days")
print(f"RMSE (Root Mean Sq Error):   {rmse:.2f} days")
print(f"R²   (Coefficient of Det):   {r2:.4f}")

# ── 7. Save Model ────────────────────────────────────────────────────────────
MODELS_DIR = os.path.join(BASE_DIR, 'app', 'backend', 'modules', 'ml', 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

MODEL_OUT = os.path.join(MODELS_DIR, 'ml_model_p6_schedule.pkl')
joblib.dump(model_p6, MODEL_OUT)
print(f"\nModel saved to {MODEL_OUT}")

# ── 8. Quick Tests ───────────────────────────────────────────────────────────
print("\n--- Quick Verification ---")
# Critical: high temp, high torque, high wear
sample_critical = np.array([[303.0, 313.0, 1300, 65.0, 240]])
pred_crit = model_p6.predict(sample_critical)[0]
print(f"Critical Machine  → Schedule in: {pred_crit:.1f} days")

# Healthy: normal conditions
sample_healthy = np.array([[298.0, 308.0, 1550, 38.0, 15]])
pred_healthy = model_p6.predict(sample_healthy)[0]
print(f"Healthy Machine   → Schedule in: {pred_healthy:.1f} days")

# Medium stress
sample_medium = np.array([[300.0, 310.0, 1400, 50.0, 120]])
pred_medium = model_p6.predict(sample_medium)[0]
print(f"Medium Stress     → Schedule in: {pred_medium:.1f} days")

print("\n✅ P6 Training Complete!")
