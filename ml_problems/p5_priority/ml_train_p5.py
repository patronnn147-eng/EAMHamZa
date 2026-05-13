"""
P5 — Work Order Priority Prediction (Optimized)
Training script: XGBoost Classifier with GridSearchCV + StratifiedKFold(5)

Improvements:
- StratifiedKFold(5) instead of cv=3 — preserves class distribution per fold
- Standalone cross_val_score: f1_macro + ordinal MAE
- Ordinal MAE: LOW<MEDIUM<HIGH<CRITICAL — penalizes CRITICAL->LOW more than CRITICAL→HIGH
"""

import pandas as pd
import numpy as np
import os
import joblib
import time
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, accuracy_score, f1_score, mean_absolute_error, make_scorer

start_time = time.time()

# ── 1. Load dataset ──────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
CSV_PATH = os.path.join(BASE_DIR, 'ai4i2020.csv')
if not os.path.exists(CSV_PATH):
    CSV_PATH = 'ai4i2020.csv'

df = pd.read_csv(CSV_PATH)
print(f"Dataset Loaded: {df.shape}")

# ── 2. Derive Ground Truth Priority ─────────────────────────────────────────
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
        return 3  # Critical
    elif dist <= 60:
        return 2  # High
    elif dist <= 120:
        return 1  # Medium
    else:
        return 0  # Low

df['Priority'] = df.apply(define_priority, axis=1)
print("Priority counts:")
print(df['Priority'].value_counts().sort_index())

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
y = df['Priority']

# ── 4. Train/Test Split ──────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ── 5. GridSearchCV with StratifiedKFold(5) ──────────────────────────────────
# StratifiedKFold(5) preserves class distribution — critical for imbalanced priority levels
print("\nRunning GridSearchCV (StratifiedKFold(5), f1_macro)...")
param_grid = {
    'n_estimators': [200, 500],
    'max_depth': [6, 10, 15],
    'learning_rate': [0.05, 0.1],
}

cv_grid = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

grid = GridSearchCV(
    estimator=XGBClassifier(
        objective='multi:softprob', num_class=4,
        eval_metric='mlogloss', random_state=42, n_jobs=-1, tree_method='hist',
    ),
    param_grid=param_grid,
    cv=cv_grid,
    scoring='f1_macro',
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
acc = accuracy_score(y_test, y_pred)
f1_macro = f1_score(y_test, y_pred, average='macro')
ordinal_mae = mean_absolute_error(y_test, y_pred)  # MAE on label indices (ordinal)

print("\n" + "="*60)
print("EVALUATION — P5 Priority Classification")
print("="*60)
print(f"Accuracy    : {acc:.4f}")
print(f"F1 Macro    : {f1_macro:.4f}")
print(f"Ordinal MAE : {ordinal_mae:.4f}  (0=perfect, 3=worst; penalizes CRITICAL->LOW heavily)")
print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=['Low', 'Medium', 'High', 'Critical']))

# ── 6b. Standalone Cross-Validation ──────────────────────────────────────────
# Ordinal MAE scorer: priority has natural order LOW<MEDIUM<HIGH<CRITICAL.
# f1_macro treats all errors equal. Ordinal MAE penalizes large label jumps.
# cross_val_score clones best_model — model untouched.
print("\n" + "="*60)
print("CROSS-VALIDATION — P5 Priority (StratifiedKFold(5))")
print("="*60)
cv_full = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

ordinal_scorer = make_scorer(mean_absolute_error, greater_is_better=False)

print("Running CV (f1_macro)...")
cv_f1 = cross_val_score(best_model, X, y, cv=cv_full, scoring='f1_macro', n_jobs=-1)
print("Running CV (accuracy)...")
cv_acc = cross_val_score(best_model, X, y, cv=cv_full, scoring='accuracy', n_jobs=-1)
print("Running CV (ordinal MAE)...")
cv_ord = cross_val_score(best_model, X, y, cv=cv_full, scoring=ordinal_scorer, n_jobs=-1)

print(f"\nF1 Macro    : {cv_f1.mean():.4f} ± {cv_f1.std():.4f}  folds={cv_f1.round(4).tolist()}")
print(f"Accuracy    : {cv_acc.mean():.4f} ± {cv_acc.std():.4f}  folds={cv_acc.round(4).tolist()}")
print(f"Ordinal MAE : {-cv_ord.mean():.4f} ± {cv_ord.std():.4f}  folds={(-cv_ord).round(4).tolist()}")

# ── 7. Save Model ────────────────────────────────────────────────────────────
MODELS_DIR = os.path.join(BASE_DIR, 'app', 'backend', 'modules', 'ml', 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

MODEL_OUT = os.path.join(MODELS_DIR, 'ml_model_p5_priority.pkl')
if os.path.exists(MODEL_OUT):
    backup = f"{MODEL_OUT}.bak_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
    os.rename(MODEL_OUT, backup)

joblib.dump({
    'model': best_model,
    'features': raw_features,
    'xgb_features': sanitized_features,
    'labels': ['Low', 'Medium', 'High', 'Critical'],
    'best_params': grid.best_params_,
    'metrics': {
        'accuracy':    round(acc, 4),
        'f1_macro':    round(f1_macro, 4),
        'ordinal_mae': round(ordinal_mae, 4),
        'cv': {
            'f1_macro_mean':    round(float(cv_f1.mean()),   4),
            'f1_macro_std':     round(float(cv_f1.std()),    4),
            'acc_mean':         round(float(cv_acc.mean()),  4),
            'acc_std':          round(float(cv_acc.std()),   4),
            'ordinal_mae_mean': round(float(-cv_ord.mean()), 4),
            'ordinal_mae_std':  round(float(cv_ord.std()),   4),
        }
    },
}, MODEL_OUT)
print(f"\nModel saved to {MODEL_OUT}")

# ── 8. Quick Test ────────────────────────────────────────────────────────────
sample_crit = np.array([[303.0, 313.0, 1300, 65.0, 240, 10.0, 84500.0]])
pred_idx = best_model.predict(sample_crit)[0]
print(f"\nManual Test (Critical Stress): Predicted Priority = {['Low', 'Medium', 'High', 'Critical'][pred_idx]}")
print(f"\n[TIME] Total training time: {time.time() - start_time:.1f}s")
