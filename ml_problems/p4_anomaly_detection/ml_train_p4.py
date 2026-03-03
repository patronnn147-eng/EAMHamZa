"""
P4 — Anomaly Detection (Unsupervised)
Training script: Isolation Forest model to detect anomalous 
machine behavior based on telemetry.
"""

import pandas as pd
import numpy as np
import os
import joblib
from sklearn.ensemble import IsolationForest

# ── 1. Load dataset ──────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
CSV_PATH = os.path.join(BASE_DIR, 'ai4i2020.csv')

if not os.path.exists(CSV_PATH):
    CSV_PATH = 'ai4i2020.csv'

df = pd.read_csv(CSV_PATH)
print(f"Dataset Loaded: {df.shape}")

# ── 2. Feature Selection ─────────────────────────────────────────────────────
features = [
    'Air temperature [K]',
    'Process temperature [K]',
    'Rotational speed [rpm]',
    'Torque [Nm]',
    'Tool wear [min]'
]

X = df[features]

# ── 3. Train Isolation Forest ────────────────────────────────────────────────
print("\nTraining Anomaly Detection Model (Isolation Forest)...")
# contamination=0.04 because approx 3.4% of rows are failures, 
# but we want to capture slightly more than just failures.
model_p4 = IsolationForest(
    n_estimators=100,
    contamination=0.04, 
    random_state=42,
    n_jobs=-1
)

model_p4.fit(X)
print("Training complete.")

# ── 4. Save Model ────────────────────────────────────────────────────────────
MODELS_DIR = os.path.join(BASE_DIR, 'app', 'backend', 'modules', 'ml', 'models')
if not os.path.exists(MODELS_DIR):
    os.makedirs(MODELS_DIR, exist_ok=True)

MODEL_OUT = os.path.join(MODELS_DIR, 'ml_model_p4_anomaly.pkl')
joblib.dump(model_p4, MODEL_OUT)
print(f"\nModel saved to {MODEL_OUT}")

# ── 5. Quick Test ────────────────────────────────────────────────────────────
# Decision function returns a score (lower = more anomalous)
# Predict returns -1 for anomaly, 1 for normal

# Normal sample
sample_normal = np.array([[300.0, 310.0, 1500, 40.0, 10]])
res_norm = model_p4.predict(sample_normal)[0]
score_norm = model_p4.decision_function(sample_normal)[0]
print(f"\nTest (Normal):  Prediction={'Anomaly' if res_norm == -1 else 'Normal'}, Score={score_norm:.4f}")

# Extreme sample
sample_anomaly = np.array([[305.0, 315.0, 3000, 75.0, 250]])
res_anom = model_p4.predict(sample_anomaly)[0]
score_anom = model_p4.decision_function(sample_anomaly)[0]
print(f"Test (Anomaly): Prediction={'Anomaly' if res_anom == -1 else 'Normal'}, Score={score_anom:.4f}")
