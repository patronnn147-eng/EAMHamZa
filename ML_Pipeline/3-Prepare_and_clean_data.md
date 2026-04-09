# ML Pipeline — EAMSagemCom
## Step 3: Prepare & Clean Data

This step transforms raw data into a clean, model-ready format for **all 6 ML problems**.

---

## Problem 1 — Binary Failure Prediction (ai4i2020.csv)

### 3.1 — Load & Inspect

```python
import pandas as pd
import numpy as np

df = pd.read_csv('ai4i2020.csv')

print(df.shape)           # (10000, 14)
print(df.isnull().sum())  # 0 — no missing values
print(df.describe())      # basic stats
print(df['Machine failure'].value_counts())
# 0    9661
# 1     339  ← Only 3.39% failures!
```

### 3.2 — Drop Irrelevant Columns

```python
df = df.drop(columns=[
    'UDI',        # Row index — not predictive
    'Product ID', # Serial number — not predictive
    'Type',       # Machine type (can be added back with encoding)
    'TWF', 'HDF', 'PWF', 'OSF', 'RNF'  # Sub-labels — kept for Problem 2 only
])
```

> ⚠️ **Data Leakage Warning:** `TWF`, `HDF`, `PWF`, `OSF`, `RNF` are sub-causes of `Machine failure`. Using them as features in P1 would give artificially perfect accuracy.

### 3.3 — Select Features & Target

```python
features = [
    'Air temperature [K]',
    'Process temperature [K]',
    'Rotational speed [rpm]',
    'Torque [Nm]',
    'Tool wear [min]'
]
X = df[features]
y = df['Machine failure']
```

### 3.4 — Handle Class Imbalance with SMOTE

```python
from imblearn.over_sampling import SMOTE
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

smote = SMOTE(random_state=42)
X_res, y_res = smote.fit_resample(X_train, y_train)
# Before: {0: 7728, 1: 272}
# After:  {0: 7728, 1: 7728} ← balanced!
```

---

## Problem 2 — Failure Type Classification (Multi-label)

Uses the **same dataset** as P1, but the target is the 5 sub-label columns.

```python
df_p2 = pd.read_csv('ai4i2020.csv')

features = ['Air temperature [K]', 'Process temperature [K]',
            'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]']

X_p2 = df_p2[features]
y_p2 = df_p2[['TWF', 'HDF', 'PWF', 'OSF', 'RNF']]  # Multi-label target

# No SMOTE needed here — use class_weight='balanced' inside the model
```

---

## Problem 3 — RUL Estimation (Regression)

Uses **internal PostgreSQL data** — intervention history per machine.

```python
from sqlalchemy import create_engine
import pandas as pd

engine = create_engine("postgresql://user:password@localhost:5432/eam_db")

df_int = pd.read_sql("""
    SELECT machine_id, date, duration
    FROM interventions
    ORDER BY machine_id, date
""", engine)

# Clean
df_int['date'] = pd.to_datetime(df_int['date'])
df_int['duration'] = df_int['duration'].fillna(df_int['duration'].median())
df_int = df_int.drop_duplicates()

# Feature: days since last intervention
df_int = df_int.sort_values(['machine_id', 'date'])
df_int['days_since_last'] = df_int.groupby('machine_id')['date'].diff().dt.days.fillna(0)

# Target: days until next intervention (RUL proxy)
df_int['rul_days'] = df_int.groupby('machine_id')['days_since_last'].shift(-1).fillna(0)

X_rul = df_int[['days_since_last', 'duration']]
y_rul = df_int['rul_days']
```

---

## Problem 4 — Anomaly Detection (Unsupervised)

No labels needed — the model learns the "normal" range from healthy machine data.

```python
df_p4 = pd.read_csv('ai4i2020.csv')

# Use only HEALTHY machines to define the normal baseline
df_normal = df_p4[df_p4['Machine failure'] == 0]

features = ['Air temperature [K]', 'Process temperature [K]',
            'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]']

X_normal = df_normal[features]  # Train on normal data only
X_all = df_p4[features]         # Score entire dataset (including failures)

# No SMOTE, no train/test split needed — unsupervised
```

---

## Problem 5 — Work Order Priority Prediction

Uses **internal PostgreSQL data** from `work_orders`, `machines`, and `interventions`.

```python
df_wo = pd.read_sql("""
    SELECT
        wo.id,
        wo.priority,
        m.type AS machine_type,
        COUNT(i.id) AS intervention_count,
        MAX(i.date) AS last_intervention
    FROM work_orders wo
    JOIN machines m ON m.id = wo.machine_id
    LEFT JOIN interventions i ON i.machine_id = wo.machine_id
    GROUP BY wo.id, wo.priority, m.type
""", engine)

# Encode categorical columns
from sklearn.preprocessing import LabelEncoder

le = LabelEncoder()
df_wo['machine_type_enc'] = le.fit_transform(df_wo['machine_type'])
df_wo['priority_enc'] = le.fit_transform(df_wo['priority'])  # LOW=0, MED=1, HIGH=2, CRITICAL=3

# Feature engineering
df_wo['days_since_last'] = (pd.Timestamp.now() - pd.to_datetime(df_wo['last_intervention'])).dt.days.fillna(999)

X_wo = df_wo[['machine_type_enc', 'intervention_count', 'days_since_last']]
y_wo = df_wo['priority_enc']
```

---

## Problem 6 — Maintenance Schedule Optimization (Time-Series)

Uses **plannings** and **interventions** tables to build a time-series dataset per machine.

```python
df_plan = pd.read_sql("""
    SELECT machine_id, date, zone, sous_zone, ordre
    FROM plannings
    ORDER BY machine_id, date
""", engine)

df_plan['date'] = pd.to_datetime(df_plan['date'])
df_plan = df_plan.sort_values(['machine_id', 'date'])

# Feature: gap between scheduled maintenances
df_plan['days_between'] = df_plan.groupby('machine_id')['date'].diff().dt.days.fillna(30)

# For forecasting, use the time series of each machine
# No SMOTE, no stratify — this is a regression/forecasting problem
```

---

## Summary Table

| Problem | Data Source | Missing Values | Imbalance Fix | Encoding Needed |
|---|---|---|---|---|
| P1 — Failure Prediction | `ai4i2020.csv` | None | SMOTE | ❌ |
| P2 — Failure Type | `ai4i2020.csv` | None | `class_weight='balanced'` | ❌ |
| P3 — RUL Estimation | PostgreSQL `interventions` | Fill median | None | ❌ |
| P4 — Anomaly Detection | `ai4i2020.csv` | None | None (unsupervised) | ❌ |
| P5 — Work Order Priority | PostgreSQL `work_orders` | days_since_last=999 | None | ✅ LabelEncoder |
| P6 — Scheduling | PostgreSQL `plannings` | Fill 30 days | None | ❌ |
