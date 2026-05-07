"""
P2 — Failure Type Classification (Optimized)
Training script: MultiOutputClassifier (XGBoost) predicting
TWF, HDF, PWF, OSF, RNF failure types from ai4i2020.csv

Improvements over baseline:
- XGBoost instead of RandomForest per label
- GridSearchCV for hyperparameter tuning
- Feature importance analysis per label
- Model saved as dict with metadata
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.multioutput import MultiOutputClassifier
from sklearn.metrics import classification_report, f1_score
from xgboost import XGBClassifier
import joblib
import os
import time

start_time = time.time()

# ── 1. Load dataset ──────────────────────────────────────────────────────────
df = pd.read_csv('ai4i2020.csv')

print(f"Dataset shape: {df.shape}")
print("\nFailure type distribution:")
labels = ['TWF', 'HDF', 'PWF', 'OSF', 'RNF']
for label in labels:
    count = df[label].sum()
    print(f"  {label}: {count} ({count/len(df)*100:.2f}%)")

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
y = df[labels]

# ── 3. Train/test split ─────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"\nTraining samples : {len(X_train)}")
print(f"Testing  samples : {len(X_test)}")

# ── 4. Calculate scale_pos_weight for most imbalanced label (HDF) ────────────
hdf_count = y_train['HDF'].sum()
spw = (len(y_train) - hdf_count) / max(hdf_count, 1)
print(f"HDF scale_pos_weight: {spw:.2f}")

# ── 5. GridSearchCV on single label (HDF) to find best params ────────────────
print("\nRunning GridSearchCV for XGBoost on HDF label (3-fold, f1 scoring)...")

param_grid = {
    'n_estimators': [200, 500],
    'max_depth': [4, 6, 8],
    'learning_rate': [0.05, 0.1],
}

# Use the label with most imbalance for tuning (HDF)
target_label = 'HDF'
label_idx = labels.index(target_label)
y_single = y_train.iloc[:, label_idx]

n_neg = (y_single == 0).sum()
n_pos = (y_single == 1).sum()
spw_label = n_neg / max(n_pos, 1)

# Use plain XGBClassifier (not MultiOutputClassifier) for GridSearchCV
grid = GridSearchCV(
    estimator=XGBClassifier(
        scale_pos_weight=spw_label,
        eval_metric='logloss',
        random_state=42,
        n_jobs=-1,
        tree_method='hist',
    ),
    param_grid=param_grid,
    cv=3,
    scoring='f1',
    n_jobs=-1,
    verbose=1,
)
grid.fit(X_train, y_single)

best_params = grid.best_params_
print(f"\n⏱ GridSearchCV took: {time.time() - start_time:.1f}s")
print(f"\n✅ Best hyper-parameters (tuned on {target_label}):")
for k, v in best_params.items():
    print(f"  {k}: {v}")

# ── 6. Train final model with best params on all labels ──────────────────────
print(f"\nTraining final MultiOutputClassifier with best params on all {len(labels)} labels...")

final_model = MultiOutputClassifier(
    XGBClassifier(
        n_estimators=best_params.get('estimator__n_estimators', 500),
        max_depth=best_params.get('estimator__max_depth', 6),
        learning_rate=best_params.get('estimator__learning_rate', 0.1),
        scale_pos_weight=spw,
        eval_metric='logloss',
        random_state=42,
        n_jobs=-1,
        tree_method='hist',
    ),
    n_jobs=-1,
)

final_model.fit(X_train, y_train)
print("Training complete.")

# ── 7. Evaluate ──────────────────────────────────────────────────────────────
y_pred = final_model.predict(X_test)

print("\n" + "="*60)
print("EVALUATION — Per-label Classification Report")
print("="*60)

f1_scores = {}
for i, label in enumerate(labels):
    f1 = f1_score(y_test.iloc[:, i], y_pred[:, i], zero_division=0)
    f1_scores[label] = round(f1, 4)
    print(f"\n--- {label} (F1={f1:.4f}) ---")
    print(classification_report(
        y_test.iloc[:, i],
        y_pred[:, i],
        target_names=["No", "Yes"],
        zero_division=0
    ))

# Feature importance per label
print("\n--- Feature Importance per Label ---")
for i, label in enumerate(labels):
    est = final_model.estimators_[i]
    importances = est.feature_importances_
    top_features = sorted(zip(features, importances), key=lambda x: -x[1])[:3]
    print(f"  {label}: {', '.join(f'{f}={imp:.3f}' for f, imp in top_features)}")

# ── 8. Save model ────────────────────────────────────────────────────────────
MODELS_DIR = os.path.join('app', 'backend', 'modules', 'ml', 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

MODEL_OUT = os.path.join(MODELS_DIR, 'ml_model_p2_failure_type.pkl')
if os.path.exists(MODEL_OUT):
    backup = f"{MODEL_OUT}.bak_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
    os.rename(MODEL_OUT, backup)
    print(f"\nBacked up old model to {backup}")

model_data = {
    'model': final_model,
    'features': features,
    'xgb_features': xgb_features,
    'labels': labels,
    'best_params': {k.replace('estimator__', ''): v for k, v in best_params.items()},
    'metrics': {'f1_per_label': f1_scores},
}
joblib.dump(model_data, MODEL_OUT)
print(f"\nModel saved to {MODEL_OUT}")

# ── 9. Quick manual test ─────────────────────────────────────────────────────
sample = np.array([[301.5, 311.0, 1450, 55.0, 200, 9.5, 79750.0]])
pred = final_model.predict(sample)[0]
proba = [est.predict_proba(sample)[0, 1] for est in final_model.estimators_]

print("\n--- Manual Test (high wear, high torque) ---")
for label, p, prob in zip(labels, pred, proba):
    flag = " <-- DETECTED" if p == 1 else ""
    print(f"  {label}: {'YES' if p==1 else 'no':3s}  (prob: {prob*100:.1f}%){flag}")

print(f"\n⏱ Total training time: {time.time() - start_time:.1f}s")
