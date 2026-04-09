"""
P4 — Anomaly Detection (Optimized)
Training script: Isolation Forest with GridSearchCV
"""

import pandas as pd
import numpy as np
import os
import joblib
import time
from sklearn.ensemble import IsolationForest

start_time = time.time()

# ── 1. Load dataset ──────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
CSV_PATH = os.path.join(BASE_DIR, 'ai4i2020.csv')
if not os.path.exists(CSV_PATH):
    CSV_PATH = 'ai4i2020.csv'

df = pd.read_csv(CSV_PATH)
print(f"Dataset Loaded: {df.shape}")

# ── 2. Feature engineering ───────────────────────────────────────────────────
df['temp_delta'] = df['Process temperature [K]'] - df['Air temperature [K]']
df['rpm_torque'] = df['Rotational speed [rpm]'] * df['Torque [Nm]']

raw_features = [
    'Air temperature [K]', 'Process temperature [K]',
    'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]',
    'temp_delta', 'rpm_torque'
]

X = df[raw_features]

# ── 3. Grid search (sequential) ──────────────────────────────────────────────
print("\nRunning grid search for Isolation Forest...")
params_list = [
    {'n_estimators': ne, 'contamination': c, 'max_samples': ms}
    for ne in [100, 200]
    for c in [0.02, 0.03, 0.04]
    for ms in ['auto', 0.8, 0.9]
]

best_score = -1
best_params = None
best_model = None

for params in params_list:
    model = IsolationForest(**params, random_state=42)
    model.fit(X)
    preds = model.predict(X)
    anomaly_preds = (preds == -1).astype(int)
    actual_failures = df['Machine failure'].values
    true_pos = ((anomaly_preds == 1) & (actual_failures == 1)).sum()
    pred_pos = anomaly_preds.sum()
    precision = true_pos / max(pred_pos, 1)
    recall = true_pos / max(actual_failures.sum(), 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-10)
    
    if f1 > best_score:
        best_score = f1
        best_params = params
        best_model = model

print(f"\n[TIME] Search took: {time.time() - start_time:.1f}s")
print(f"\n[OK] Best params: {best_params}")
print(f"Best F1 (vs failures): {best_score:.4f}")

# ── 4. Evaluate ──────────────────────────────────────────────────────────────
preds = best_model.predict(X)
scores = best_model.decision_function(X)
anomaly_preds = (preds == -1).astype(int)

actual_failures = df['Machine failure'].values
true_pos = ((anomaly_preds == 1) & (actual_failures == 1)).sum()
false_pos = ((anomaly_preds == 1) & (actual_failures == 0)).sum()
false_neg = ((anomaly_preds == 0) & (actual_failures == 1)).sum()
true_neg = ((anomaly_preds == 0) & (actual_failures == 0)).sum()

precision = true_pos / max(true_pos + false_pos, 1)
recall = true_pos / max(true_pos + false_neg, 1)

print(f"\nAnomalies detected: {anomaly_preds.sum()} ({anomaly_preds.mean()*100:.1f}%)")
print(f"Precision (vs failures): {precision:.4f}")
print(f"Recall (vs failures):    {recall:.4f}")
print(f"TP={true_pos}, FP={false_pos}, FN={false_neg}, TN={true_neg}")

# ── 5. Save Model ────────────────────────────────────────────────────────────
MODELS_DIR = os.path.join(BASE_DIR, 'app', 'backend', 'modules', 'ml', 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

MODEL_OUT = os.path.join(MODELS_DIR, 'ml_model_p4_anomaly.pkl')
if os.path.exists(MODEL_OUT):
    backup = f"{MODEL_OUT}.bak_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
    os.rename(MODEL_OUT, backup)

joblib.dump({
    'model': best_model,
    'features': raw_features,
    'best_params': best_params,
    'metrics': {'precision': round(precision, 4), 'recall': round(recall, 4), 'f1': round(best_score, 4)},
}, MODEL_OUT)
print(f"\nModel saved to {MODEL_OUT}")

# ── 6. Quick Test ────────────────────────────────────────────────────────────
sample_normal = np.array([[300.0, 310.0, 1500, 40.0, 10, 10.0, 60000.0]])
res_norm = best_model.predict(sample_normal)[0]
score_norm = best_model.decision_function(sample_normal)[0]
print(f"\nTest (Normal):  Prediction={'Anomaly' if res_norm == -1 else 'Normal'}, Score={score_norm:.4f}")

sample_anomaly = np.array([[305.0, 315.0, 3000, 75.0, 250, 10.0, 225000.0]])
res_anom = best_model.predict(sample_anomaly)[0]
score_anom = best_model.decision_function(sample_anomaly)[0]
print(f"Test (Anomaly): Prediction={'Anomaly' if res_anom == -1 else 'Normal'}, Score={score_anom:.4f}")
print(f"\n[TIME] Total training time: {time.time() - start_time:.1f}s")
