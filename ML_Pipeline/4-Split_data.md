# ML Pipeline — EAMSagemCom
## Step 4: Split Data (Train / Test)

Each problem has a different splitting strategy depending on whether it is supervised, multi-label, or time-series.

---

## Problem 1 — Binary Failure Prediction

Standard stratified 80/20 split — preserves the 3.39% failure ratio in both sets.

```python
from sklearn.model_selection import train_test_split
from imblearn.over_sampling import SMOTE

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y        # Keeps failure rate consistent in both sets
)

# Apply SMOTE only on training data
smote = SMOTE(random_state=42)
X_train_res, y_train_res = smote.fit_resample(X_train, y_train)
```

| Set | Rows | Failures |
|---|---|---|
| X_train (before SMOTE) | 8,000 | ~272 (3.4%) |
| X_train_res (after SMOTE) | ~15,456 | ~7,728 (50%) |
| X_test | 2,000 | ~67 (3.4%) |

> ✅ SMOTE applied **after** split — never before (avoids leakage).

---

## Problem 2 — Failure Type Classification (Multi-label)

Same dataset split as P1, but `y` is now the 5 sub-label columns.

```python
from sklearn.model_selection import train_test_split

X_train_p2, X_test_p2, y_train_p2, y_test_p2 = train_test_split(
    X_p2, y_p2,      # y_p2 = df[['TWF','HDF','PWF','OSF','RNF']]
    test_size=0.2,
    random_state=42
    # No stratify for multi-label — not directly supported
)
```

> Use `class_weight='balanced'` inside the model instead of SMOTE for multi-label.

---

## Problem 3 — RUL Estimation (Regression)

No stratification needed — this is a regression problem. Use a simple 80/20 split.

```python
from sklearn.model_selection import train_test_split

X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(
    X_rul, y_rul,
    test_size=0.2,
    random_state=42
)
```

---

## Problem 4 — Anomaly Detection (Unsupervised)

No split needed in the traditional sense — the model trains **only on normal data** and then scores everything:

```python
# Train on healthy machines only
X_train_ad = X_normal   # Healthy machines from ai4i2020.csv (Machine failure == 0)

# Score on all data — model flags anything that deviates from normal
X_score_ad = X_all      # Full dataset including failures
```

> No test/train split — Isolation Forest is unsupervised and doesn't learn from labels.

---

## Problem 5 — Work Order Priority Prediction

Standard 80/20 split on the PostgreSQL-derived dataset.

```python
from sklearn.model_selection import train_test_split

X_train_wo, X_test_wo, y_train_wo, y_test_wo = train_test_split(
    X_wo, y_wo,
    test_size=0.2,
    random_state=42,
    stratify=y_wo    # Preserve class distribution (LOW/MED/HIGH/CRITICAL)
)
```

---

## Problem 6 — Maintenance Scheduling (Time-Series)

Time-series data must be split **chronologically** — never randomly, to avoid future leakage.

```python
# Split by time (last 20% of dates = test)
split_idx = int(len(df_plan) * 0.8)
df_train_ts = df_plan.iloc[:split_idx]
df_test_ts  = df_plan.iloc[split_idx:]

X_train_ts = df_train_ts[['days_between']]
y_train_ts = df_train_ts['days_between'].shift(-1).dropna()  # Next gap = target
```

> ⚠️ **Never use random shuffling on time-series data** — it creates future leakage (the model would see future dates during training).

---

## Cross-Validation Strategy (P1, P2, P5)

For supervised classification problems, use `GridSearchCV` with `cv=3`:

```python
from sklearn.model_selection import GridSearchCV

grid = GridSearchCV(
    estimator=model,
    param_grid={...},
    cv=3,           # 3-fold cross-validation on training data
    scoring='f1',   # F1 for imbalanced problems
    n_jobs=-1
)
grid.fit(X_train_res, y_train_res)
```

---

## Summary

| Problem | Split Strategy | Test Size | Stratify | Notes |
|---|---|---|---|---|
| P1 — Failure Prediction | Random + SMOTE | 20% | ✅ Yes | SMOTE after split |
| P2 — Failure Type | Random | 20% | ❌ No | Multi-label |
| P3 — RUL Estimation | Random | 20% | ❌ No | Regression |
| P4 — Anomaly Detection | None (unsupervised) | — | — | Train on normal only |
| P5 — Work Order Priority | Random | 20% | ✅ Yes | DB data |
| P6 — Scheduling | **Chronological** | Last 20% | ❌ No | Time-series |
