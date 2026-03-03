"""
P2 — Failure Type Classification
Training script: MultiOutputClassifier (Random Forest) predicting
TWF, HDF, PWF, OSF, RNF failure types from ai4i2020.csv

Pipeline references:
  - 3-Prepare_and_clean_data.md  → feature selection, no SMOTE for multi-label
  - 5-Choose_a_model.md          → MultiOutputClassifier(RandomForest, class_weight='balanced')
  - 6-Train_the_model.md         → fit on X_train_p2 / y_train_p2
  - 7-Evaluate_performance.md    → F1 per label, focus on HDF recall
  - 8-Tune_and_improve.md        → temp_delta feature engineering
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.metrics import classification_report
import joblib

# ── 1. Load dataset ──────────────────────────────────────────────────────────
df = pd.read_csv('ai4i2020.csv')

print(f"Dataset shape: {df.shape}")
print("\nFailure type distribution:")
labels = ['TWF', 'HDF', 'PWF', 'OSF', 'RNF']
for label in labels:
    count = df[label].sum()
    print(f"  {label}: {count} ({count/len(df)*100:.2f}%)")

# ── 2. Feature engineering (from 8-Tune_and_improve.md) ─────────────────────
# temp_delta: HDF is driven by the gap between process and air temperature
df['temp_delta'] = df['Process temperature [K]'] - df['Air temperature [K]']

features = [
    'Air temperature [K]',
    'Process temperature [K]',
    'Rotational speed [rpm]',
    'Torque [Nm]',
    'Tool wear [min]',
    'temp_delta',       # Engineered feature — improves HDF recall
]

X = df[features]
y = df[labels]          # 5 binary columns: TWF, HDF, PWF, OSF, RNF

# ── 3. Train/test split (from 4-Split_data.md — no stratify for multi-label) ─
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"\nTraining samples : {len(X_train)}")
print(f"Testing  samples : {len(X_test)}")

# ── 4. Train MultiOutputClassifier (from 6-Train_the_model.md) ──────────────
# One RandomForestClassifier per label: TWF, HDF, PWF, OSF, RNF
model_p2 = MultiOutputClassifier(
    RandomForestClassifier(
        n_estimators=200,
        class_weight='balanced',   # Handles per-label imbalance
        random_state=42,
        n_jobs=-1,
    )
)

print("\nTraining MultiOutputClassifier (5 independent RF classifiers)...")
model_p2.fit(X_train, y_train)
print("Training complete.")

# ── 5. Evaluate (from 7-Evaluate_performance.md) ────────────────────────────
y_pred = model_p2.predict(X_test)

print("\n" + "="*60)
print("EVALUATION — Per-label Classification Report")
print("="*60)
for i, label in enumerate(labels):
    print(f"\n--- {label} ---")
    print(classification_report(
        y_test.iloc[:, i],
        y_pred[:, i],
        target_names=["No", "Yes"],
        zero_division=0
    ))

# ── 6. Save model ────────────────────────────────────────────────────────────
MODEL_OUT = 'ml_model_p2_failure_type.pkl'
joblib.dump({'model': model_p2, 'features': features, 'labels': labels}, MODEL_OUT)
print(f"\nModel saved to {MODEL_OUT}")

# ── 7. Quick manual test ─────────────────────────────────────────────────────
sample = np.array([[301.5, 311.0, 1450, 55.0, 200, 9.5]])   # high tool wear + temp_delta
sample_df = pd.DataFrame(sample, columns=features)
pred = model_p2.predict(sample_df)[0]
proba = [est.predict_proba(sample_df)[0, 1] for est in model_p2.estimators_]

print("\n--- Manual Test (high wear, high torque) ---")
for label, p, prob in zip(labels, pred, proba):
    flag = " <-- DETECTED" if p == 1 else ""
    print(f"  {label}: {'YES' if p==1 else 'no':3s}  (prob: {prob*100:.1f}%){flag}")
