# config.py

## What it does
Stores every number the ML system uses for decisions — thresholds, defaults, file paths.

## Why it exists
Previously these numbers were scattered across 4 files. If you wanted to change the anomaly sensitivity, you had to find it in 3 different places. Now it's one file.

## Inputs / Outputs
- Input: optional environment variables (e.g. `ML_P4_ANOMALY_THRESHOLD=0.7`)
- Output: a `config` object that every other module imports

## Who calls it
Every module in `core/` and most modules in `src/`.

## What breaks if this file has a bug
Every model threshold and path is wrong. The system may reject all inputs as anomalies or accept none.

## Key values
| Setting | Default | Meaning |
|---------|---------|---------|
| `p4_anomaly_threshold` | 0.5 | Score above this = anomaly flagged |
| `p1_risk_critical` | 75.0 | Failure probability above this = CRITICAL |
| `dst_conflict_threshold` | 0.8 | Above this the system uses conservative fusion |
| `models_dir` | `../models/` | Where trained model files (.pkl) are stored |
