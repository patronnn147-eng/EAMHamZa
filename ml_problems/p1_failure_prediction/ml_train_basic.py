"""
P1 — Failure Prediction (Optimized)
Training script: XGBoost + SMOTE + 5-fold GridSearchCV
Predicts binary machine failure from ai4i2020.csv telemetry data.

Improvements over baseline:
- XGBoost instead of RandomForest (better on imbalanced data)
- 5-fold stratified CV instead of 3-fold
- Expanded hyperparameter search grid
- scale_pos_weight for class imbalance
- ROC-AUC and PR-AUC metrics
- Model saved as dict with metadata
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_auc_score, precision_recall_curve, auc
)
from xgboost import XGBClassifier
from imblearn.over_sampling import SMOTE
import joblib
import os
import time

start_time = time.time()

# ── 1. Load dataset ──────────────────────────────────────────────────────────
df = pd.read_csv('ai4i2020.csv')
print(f"Dataset shape: {df.shape}")
print(f"Failure rate: {df['Machine failure'].mean()*100:.2f}%")

# ── 2. Feature engineering ───────────────────────────────────────────────────
df['temp_delta'] = df['Process temperature [K]'] - df['Air temperature [K]']
df['rpm_torque'] = df['Rotational speed [rpm]'] * df['Torque [Nm]']

features = [
    'Air temperature [K]',
    'Process temperature [K]',
    'Rotational speed [rpm]',
    'Torque [Nm]',
    'Tool wear [min]',
    'temp_delta',
    'rpm_torque',
]

# XGBoost doesn't allow [, ] or < in feature names
xgb_features = [f.replace('[', '').replace(']', '') for f in features]

X = df[features].copy()
X.columns = xgb_features
y = df['Machine failure']

# ── 3. Train/test split (stratified) ─────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"\nTraining set: {len(X_train)} (failures: {y_train.sum()})")
print(f"Test set:     {len(X_test)}  (failures: {y_test.sum()})")

# ── 4. SMOTE oversampling ────────────────────────────────────────────────────
smote = SMOTE(random_state=42)
X_res, y_res = smote.fit_resample(X_train, y_train)
print(f"After SMOTE:  {len(X_res)} (failures: {y_res.sum()})")

# ── 5. Calculate scale_pos_weight for XGBoost ────────────────────────────────
n_neg = (y_res == 0).sum()
n_pos = (y_res == 1).sum()
spw = n_neg / n_pos
print(f"scale_pos_weight: {spw:.2f}")

# ── 6. GridSearchCV with expanded params ─────────────────────────────────────
param_grid = {
    'n_estimators': [200, 500],
    'learning_rate': [0.05, 0.1],
    'max_depth': [4, 6],
    'subsample': [0.8],
    'colsample_bytree': [0.8],
}

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

print("\nRunning GridSearchCV (5-fold, f1 scoring)...")
grid = GridSearchCV(
    estimator=XGBClassifier(
        scale_pos_weight=spw,
        use_label_encoder=False,
        eval_metric='logloss',
        random_state=42,
        n_jobs=-1,
        tree_method='hist',
    ),
    param_grid=param_grid,
    cv=cv,
    scoring='f1',
    n_jobs=-1,
    verbose=1,
)
grid.fit(X_res, y_res)

best_model = grid.best_estimator_
print(f"\n⏱ GridSearchCV took: {time.time() - start_time:.1f}s")
print("\n✅ Best hyper-parameters:")
for k, v in grid.best_params_.items():
    print(f"  {k}: {v}")

# ── 7. Evaluate on held-out test set ─────────────────────────────────────────
y_pred = best_model.predict(X_test)
y_proba = best_model.predict_proba(X_test)[:, 1]

print("\n" + "="*60)
print("EVALUATION — P1 Failure Prediction")
print("="*60)
print("\n--- Confusion Matrix ---")
print(confusion_matrix(y_test, y_pred))
print("\n--- Classification Report ---")
print(classification_report(y_test, y_pred, target_names=['Healthy', 'Failure']))

# ROC-AUC
roc_auc = roc_auc_score(y_test, y_proba)
print(f"\nROC-AUC: {roc_auc:.4f}")

# PR-AUC
precision, recall, _ = precision_recall_curve(y_test, y_proba)
pr_auc = auc(recall, precision)
print(f"PR-AUC:  {pr_auc:.4f}")

# Feature importance
print("\n--- Feature Importance ---")
importances = best_model.feature_importances_
for feat, imp in sorted(zip(features, importances), key=lambda x: -x[1]):
    print(f"  {feat:30s} {imp:.4f}")

# ── 8. Save model with metadata ──────────────────────────────────────────────
MODELS_DIR = os.path.join('app', 'backend', 'modules', 'ml', 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

model_data = {
    'model': best_model,
    'features': features,  # Original names for display
    'xgb_features': xgb_features,  # Sanitized names for XGBoost
    'best_params': grid.best_params_,
    'metrics': {
        'roc_auc': round(roc_auc, 4),
        'pr_auc': round(pr_auc, 4),
        'f1_failure': round(float(classification_report(y_test, y_pred, output_dict=True).get('Failure', {}).get('f1-score', 0)), 4),
    }
}

model_path = os.path.join(MODELS_DIR, 'basic_machine_model.pkl')
# Backup old model
if os.path.exists(model_path):
    backup = f"{model_path}.bak_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
    os.rename(model_path, backup)
    print(f"\nBacked up old model to {backup}")

joblib.dump(model_data, model_path)
print(f"\nModel saved to {model_path}")

# ── 9. Quick manual test ─────────────────────────────────────────────────────
sample_input = np.array([[300.0, 310.0, 1500, 40.0, 5, 10.0, 60000.0]])
prediction = best_model.predict(sample_input)
probability = best_model.predict_proba(sample_input)[0]

print("\n--- Manual Test ---")
print(f"Input: {sample_input[0]}")
print(f"Prediction: {'FAILURE' if prediction[0] == 1 else 'HEALTHY'}")
print(f"Probability: Healthy={probability[0]:.4f}, Failure={probability[1]:.4f}")

print(f"\n⏱ Total training time: {time.time() - start_time:.1f}s")
