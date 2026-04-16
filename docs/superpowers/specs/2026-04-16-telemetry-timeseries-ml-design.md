# Telemetry Time-Series ML Pipeline Design
**Date:** 2026-04-16
**Branch:** clean_Phase_1

---

## Problem Statement

The ML health/RUL pipeline currently reads sensor values (`air_temperature`, `process_temperature`, `rotational_speed`, `torque`, `tool_wear`) from static columns on the `machines` table. These are stale snapshots that never reliably update. Real technician-recorded readings live in `machine_telemetry_logs` as timestamped rows — one per work order completion — but the ML pipeline ignores them entirely.

Additionally `machine_telemetry_logs` uses placeholder column names (`temperature`, `vibration`, `rpm`, `power`) that don't match ML model feature names, and the ML models receive single scalars when several of them (PINN, Kalman) were already designed for time-series input.

---

## Goals

1. Make `machine_telemetry_logs` the single source of truth for sensor data
2. Rename its columns to match ML feature names
3. Remove redundant static telemetry columns from `machines`
4. Feed the full historical list to the ML pipeline (not just the latest scalar)
5. Use the latest entry as the scalar for current P1–P6 model calls (backward-compatible)
6. Add a degradation rate derived from the list to improve RUL accuracy
7. Properly wire PINN, Kalman, CUSUM, Mahalanobis, and Fine-Gray to use the full time series

---

## Approach: Option B — Latest + Derived Trend Scalar

- Query all `machine_telemetry_logs` rows for a machine ordered `recorded_at ASC`
- Use `entries[-1]` (latest) as the scalar feature vector for all P1–P6 model calls — no ML microservice interface changes
- Compute degradation rate per sensor: `(latest - first) / max(n-1, 1)`
- Pass the full list to time-series-aware models (PINN, Kalman, CUSUM, Mahalanobis, Fine-Gray)
- Fall back to hardcoded defaults if no telemetry exists yet for a machine

---

## Section 1 — Database Schema Changes

### `machine_telemetry_logs` — column renames

| Old name | New name | Type |
|---|---|---|
| `temperature` | `air_temperature` | Float |
| `vibration` | `process_temperature` | Float |
| `rpm` | `rotational_speed` | Integer |
| `power` | `tool_wear` | Float |
| `torque` | `torque` | Float (unchanged) |
| All metadata cols | unchanged | — |

All existing row data is preserved. Rename is non-destructive.

### `machines` — columns to drop

`air_temperature`, `process_temperature`, `rotational_speed`, `torque`, `tool_wear`

These were static placeholders updated on work order completion. Replaced entirely by `machine_telemetry_logs`.

### Migration

Single Alembic migration file:
1. `ALTER TABLE machine_telemetry_logs RENAME COLUMN temperature TO air_temperature` (x4)
2. `ALTER TABLE machines DROP COLUMN air_temperature` (x5)

---

## Section 2 — RUL Calculator & ML Router

### `modules/ml/router.py`

Both `/unified-health` and `/prediction` endpoints:
- Query all `machine_telemetry_logs` rows for `machine_id` ordered `recorded_at ASC`
- Pass `telemetry_entries` list to `RULCalculator.calculate_rul()`
- Remove all `getattr(machine, "air_temperature", 300)` lines

### `modules/ml/rul_calculator.py`

New signature:
```python
def calculate_rul(
    machine: Machines,
    interventions: List[Ordres_intervention],
    telemetry_entries: List[MachineTelemetry],  # NEW
    open_work_orders: int = 0,
    recent_interventions: int = 0,
    fusion_result: Optional[Dict] = None,
) -> Dict
```

Logic:
- If `telemetry_entries` is empty → use hardcoded defaults (300, 310, 1500, 40, 0)
- If not empty → `latest = entries[-1]`, extract scalars for ML model calls
- Compute degradation rate: `(latest.air_temperature - entries[0].air_temperature) / max(len(entries)-1, 1)` for each sensor
- Apply degradation rate as a multiplier on `rul_days`: faster degradation → proportionally shorter RUL
- Also expose `data_points = len(telemetry_entries)` in the response

---

## Section 3 — Work Order Completion Handlers

### Both handlers (technicien + chetop)

Update `MachineTelemetry(...)` insert to use new column names:
```python
MachineTelemetry(
    air_temperature=...,
    process_temperature=...,
    rotational_speed=...,
    torque=...,
    tool_wear=...,
)
```

Remove the `machines` update block from `chetop/routes/work_orders.py`:
```python
# DELETE THIS ENTIRE BLOCK:
machine.air_temperature = payload.air_temperature
machine.process_temperature = payload.process_temperature
machine.rotational_speed = payload.rotational_speed
machine.torque = payload.torque
machine.tool_wear = payload.tool_wear
```

### Schemas (`technicien/schemas_telemetry.py`)

Update Pydantic response schemas that serialize `MachineTelemetry` rows to use new field names.

---

## Section 4 — ML Microservice Model Updates

All models receive the telemetry list from `RULCalculator`. The ML microservice HTTP interface (`/predict-all`) is unchanged — it still accepts scalars.

### PINN (`pinn_rul.py`)
Already accepts `List[FeatureSnapshot]`. Build snapshot list from `telemetry_entries` and pass it. No algorithm change.

### Kalman Filter (`kalman_estimator.py`)
Already has `smooth(obs_sequence)`. Call `smooth(obs_list)` with all historical observations instead of a single `update()`. Returns smoothed current state — eliminates 0/100 score swings from single noisy readings.

### CUSUM (`anomaly_cusum.py`)
Before scoring the latest point, replay the full history list through sequential `update()` calls to initialize cumulative sum state. Alarm threshold then reflects real accumulated drift.

### Mahalanobis + GMM (`health_index.py`)
Compute `mean`, `std`, and `trend_slope` across the list for each feature. Pass these as a richer observation vector to the distance scorer. Health index reflects the machine's position relative to its own historical baseline.

### Fine-Gray / Cox PH (`survival_model.py`)
Restructure telemetry list into survival episodes: each consecutive pair of readings becomes `(duration, air_temperature, rotational_speed, torque, tool_wear)`. Complete and wire `fit_from_logs()` into the prediction path.

### DST Fusion (`dst_fusion.py`)
No changes — fuses whatever the above models return.

---

## Section 5 — Fallback Strategy

When `telemetry_entries` is empty (new machine, no work orders completed yet):
- Scalar defaults: `air=300.0, process=310.0, rpm=1500, torque=40.0, tool_wear=0`
- Degradation rate: `0.0` for all sensors
- PINN, Kalman, CUSUM receive a single synthetic snapshot built from defaults
- Health score defaults to 100 (new machine assumption)
- `data_points: 0` exposed in response

---

## Files Changed

| # | File | Change |
|---|---|---|
| 1 | `alembic/versions/xxxx_telemetry_rename.py` (new) | Rename 4 cols, drop 5 cols |
| 2 | `models/machine_telemetry.py` | Rename column definitions |
| 3 | `models/machines.py` | Remove 5 column definitions |
| 4 | `modules/ml/router.py` | Query telemetry list, pass to RUL calc |
| 5 | `modules/ml/rul_calculator.py` | Accept list, compute degradation rate, pipe to models |
| 6 | `modules/technicien/technicien_work_orders.py` | Update insert col names |
| 7 | `modules/chetop/routes/work_orders.py` | Update insert col names, remove machines update block |
| 8 | `modules/technicien/schemas_telemetry.py` | Update Pydantic field names |
| 9 | `ml-microservice/src/pinn_rul.py` | Pipe in snapshot list |
| 10 | `ml-microservice/src/kalman_estimator.py` | Call `smooth()` with full list |
| 11 | `ml-microservice/src/anomaly_cusum.py` | Replay history through `update()` |
| 12 | `ml-microservice/src/health_index.py` | Compute stats from list before scoring |
| 13 | `ml-microservice/src/survival_model.py` | Wire `fit_from_logs()` into prediction path |

---

## Non-Goals

- No changes to ML microservice HTTP interface (`/predict-all` still accepts scalars)
- No frontend changes — field names in the completion form stay the same
- No model retraining required
- No changes to DST fusion logic
