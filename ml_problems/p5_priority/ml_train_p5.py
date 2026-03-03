"""
P5 — Work Order Priority Prediction
Training script: Classification model (Random Forest) predicting 
the priority level: Low (0), Medium (1), High (2), Critical (3).

Strategy:
- Derive Priority based on ground-truth RUL and Failure events.
- Features: Air temp, Process temp, RPM, Torque, Tool wear.
"""

import pandas as pd
import numpy as np
import os
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

# ── 1. Load dataset ──────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
CSV_PATH = os.path.join(BASE_DIR, 'ai4i2020.csv')

if not os.path.exists(CSV_PATH):
    CSV_PATH = 'ai4i2020.csv'

df = pd.read_csv(CSV_PATH)
print(f"Dataset Loaded: {df.shape}")

# ── 2. Derive Ground Truth Priority ─────────────────────────────────────────
# RUL calculation (mirrors P3)
failure_indices = df.index[df['Machine failure'] == 1].tolist()

def get_dist_to_failure(idx):
    future_failures = [f for f in failure_indices if f >= idx]
    if not future_failures:
        return 500
    return future_failures[0] - idx

print("Calculating Ground Truth Priority levels...")
df['dist_to_failure'] = [get_dist_to_failure(i) for i in range(len(df))]

def define_priority(row):
    dist = row['dist_to_failure']
    failure = row['Machine failure']
    
    if failure == 1 or dist <= 15:
        return 3 # Critical
    elif dist <= 60:
        return 2 # High
    elif dist <= 120:
        return 1 # Medium
    else:
        return 0 # Low

df['Priority'] = df.apply(define_priority, axis=1)

print("Priority counts:")
print(df['Priority'].value_counts())

# ── 3. Feature Selection ─────────────────────────────────────────────────────
features = [
    'Air temperature [K]',
    'Process temperature [K]',
    'Rotational speed [rpm]',
    'Torque [Nm]',
    'Tool wear [min]'
]

X = df[features]
y = df['Priority']

# ── 4. Train/Test Split ──────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ── 5. Train Random Forest ──────────────────────────────────────────────────
# Using Random Forest for multi-class classification
print("\nTraining Priority Classifier (Random Forest)...")
model_p5 = RandomForestClassifier(
    n_estimators=200,
    max_depth=12,
    random_state=42,
    n_jobs=-1
)

model_p5.fit(X_train, y_train)
print("Training complete.")

# ── 6. Evaluate ──────────────────────────────────────────────────────────────
y_pred = model_p5.predict(X_test)
acc = accuracy_score(y_test, y_pred)

print("\n" + "="*60)
print("EVALUATION — Priority Classification")
print("="*60)
print(f"Accuracy: {acc:.4f}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=['Low', 'Medium', 'High', 'Critical']))

# ── 7. Save Model ────────────────────────────────────────────────────────────
MODELS_DIR = os.path.join(BASE_DIR, 'app', 'backend', 'modules', 'ml', 'models')
if not os.path.exists(MODELS_DIR):
    os.makedirs(MODELS_DIR, exist_ok=True)

MODEL_OUT = os.path.join(MODELS_DIR, 'ml_model_p5_priority.pkl')
# Save labels along with the model
save_data = {
    'model': model_p5,
    'labels': ['Low', 'Medium', 'High', 'Critical']
}
joblib.dump(save_data, MODEL_OUT)
print(f"\nModel saved to {MODEL_OUT}")

# ── 8. Quick Test ────────────────────────────────────────────────────────────
# Critical sample
sample_crit = np.array([[303.0, 313.0, 1300, 65.0, 240]])
pred_idx = model_p5.predict(sample_crit)[0]
print(f"\nManual Test (Critical Stress): Predicted Priority = {save_data['labels'][pred_idx]}")
