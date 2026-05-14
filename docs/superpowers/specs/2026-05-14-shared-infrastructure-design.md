# Sub-project 1: Shared Infrastructure — Design Spec

**Date:** 2026-05-14  
**Status:** Approved  
**Scope:** `app/ml-microservice/src/core/` (new) + targeted touches to existing files  
**Unblocks:** Sub-project 2 (Inference Architecture), Sub-project 3 (Training Pipelines)

---

## Problem Statement

Three concrete problems in the current `src/` flat structure:

1. **Mixed loader patterns** — P1 uses `global _MODEL` + lazy `get_model()`. P2–P6 eager-load at module import (crash on missing file). No uniform contract.
2. **Duplicated feature derivation** — `temp_delta = process - air` and `rpm_torque = rpm * torque / 1000` appear independently in P1, P2, and P3 prediction methods.
3. **Config sprawl** — thresholds (`0.5`, `0.8`, `75.0`, `50.0`) hardcoded across `predictions.py`, `router.py`, `dst_fusion.py` with no single source of truth.

---

## Approach

Pydantic config + unified loader + feature pipeline (Approach B).

**Not chosen:**
- Approach A (thin layer) — doesn't fix config sprawl or pkl contract gaps
- Approach C (plugin registry) — premature abstraction for 6 fixed models

---

## Full Target Folder Structure

```
src/
  core/                          ← SUB-1: created now
    config.py                    ← Pydantic BaseSettings — all params, thresholds, paths
    config.md
    feature_pipeline.py          ← build_5(), build_7() — canonical feature derivation
    feature_pipeline.md
    model_loader.py              ← unified lazy-load, @lru_cache, contract validation
    model_loader.md
    feature_validator.py         ← renamed from feature_store.py: input validation
    feature_validator.md

  inference/                     ← SUB-2: split from predictions.py
    failure_probability.py       ← P1
    failure_probability.md
    failure_classification.py    ← P2
    failure_classification.md
    rul_estimation.py            ← P3
    rul_estimation.md
    anomaly_detection.py         ← P4
    anomaly_detection.md
    work_order_priority.py       ← P5
    work_order_priority.md
    maintenance_schedule.py      ← P6
    maintenance_schedule.md

  wave2/                         ← SUB-2: move existing Wave 2 files here
    dst_fusion.py
    dst_fusion.md
    health_index.py
    health_index.md
    kalman_estimator.py
    kalman_estimator.md
    survival_model.py
    survival_model.md
    anomaly_cusum.py
    anomaly_cusum.md
    pinn_rul.py
    pinn_rul.md
    moment_estimator.py
    moment_estimator.md
    drift_detector.py
    drift_detector.md
    drift_monitor.py
    drift_monitor.md
    xai_service.py
    xai_service.md

  api/                           ← SUB-2: split from router.py
    routes.py
    routes.md
    schemas.py
    schemas.md

  utils/                         ← SUB-2: move existing
    cache.py
    cache.md
    rate_limiter.py
    rate_limiter.md
    model_registry.py
    model_registry.md
```

Each `.md` follows this template:
```markdown
# [filename]
## What it does
## Why it exists
## Inputs / Outputs
## Who calls it
## What breaks if this file has a bug
```

---

## Component Designs (Sub-1 Scope)

### `core/config.py`

Single Pydantic `BaseSettings` singleton. All values env-overridable via `ML_` prefix.

```python
from pathlib import Path
from pydantic_settings import BaseSettings

class MLConfig(BaseSettings):
    # Paths
    models_dir: Path = Path(__file__).parent.parent / "models"

    # P1 — risk level thresholds
    p1_risk_medium: float = 25.0
    p1_risk_high: float = 50.0
    p1_risk_critical: float = 75.0

    # P4 — anomaly detection
    p4_anomaly_threshold: float = 0.5

    # DST fusion
    dst_conflict_threshold: float = 0.8

    # Feature defaults (used when sensor data missing)
    default_air_temp: float = 298.0
    default_process_temp: float = 308.0
    default_rpm: int = 1500
    default_torque: float = 40.0
    default_tool_wear: int = 0

    class Config:
        env_prefix = "ML_"

config = MLConfig()  # module-level singleton — import this, never instantiate again
```

Replaces: all hardcoded threshold literals in `dst_fusion.py`, `router.py`, `predictions.py`.

---

### `core/feature_pipeline.py`

Eliminates 3× duplication of derived feature computation.

```python
from dataclasses import dataclass
from typing import List

@dataclass
class SensorReading:
    air_temp: float
    process_temp: float
    rpm: float
    torque: float
    tool_wear: float

class FeaturePipeline:
    @staticmethod
    def build_5(r: SensorReading) -> List[float]:
        """5 raw sensor features. Used by: P3, P4."""
        return [r.air_temp, r.process_temp, r.rpm, r.torque, r.tool_wear]

    @staticmethod
    def build_7(r: SensorReading) -> List[float]:
        """7 features: 5 raw + temp_delta + rpm_torque. Used by: P1, P2."""
        temp_delta = r.process_temp - r.air_temp
        rpm_torque = (r.rpm * r.torque) / 1000.0
        return [r.air_temp, r.process_temp, r.rpm, r.torque, r.tool_wear,
                temp_delta, rpm_torque]
```

**Who calls what:**
| Model | Method |
|-------|--------|
| P1 | `build_7()` |
| P2 | `build_7()` |
| P3 | `build_5()` (then XGBoost adds derived internally) |
| P4 | `build_5()` (5-sensor ensemble) |
| P5 | `build_7()` |
| P6 | `build_7()` |

---

### `core/model_loader.py`

Uniform lazy-load with `@lru_cache`. Every model follows identical pattern. Missing file → `None`, never exception.

```python
from functools import lru_cache
from pathlib import Path
import joblib
import logging
from .config import config

logger = logging.getLogger(__name__)

def _extract(data, key: str = "model"):
    """Extract model from pkl dict or return bare model for legacy pkls."""
    if isinstance(data, dict):
        return data.get(key)
    return data

def _load(path: Path, label: str):
    """Safe load — returns None on any failure."""
    if not path.exists():
        logger.error(f"[MISSING] {label} pkl not found: {path}")
        return None
    try:
        return joblib.load(path)
    except Exception as e:
        logger.error(f"[ERROR] {label} pkl failed to load: {e}")
        return None

@lru_cache(maxsize=1)
def load_p1():
    data = _load(config.models_dir / "basic_machine_model.pkl", "P1")
    return _extract(data)

@lru_cache(maxsize=1)
def load_p2():
    data = _load(config.models_dir / "ml_model_p2_failure_type.pkl", "P2")
    if data is None:
        return None
    return {"model": data["model"], "labels": data.get("labels", [])}

@lru_cache(maxsize=1)
def load_p3():
    data = _load(config.models_dir / "ml_model_p3_rul.pkl", "P3")
    return _extract(data)

@lru_cache(maxsize=1)
def load_p4():
    data = _load(config.models_dir / "ml_model_p4_anomaly_v2.pkl", "P4")
    if data is None:
        return None
    return {
        "model":          data.get("iso_model"),
        "weights":        data.get("weights", {}),
        "thresholds":     data.get("thresholds", {}),
        "training_stats": data.get("training_stats", {}),
        "ae_scaler":      data.get("ae_scaler"),
        "autoencoder":    data.get("autoencoder"),
    }

@lru_cache(maxsize=1)
def load_p5():
    data = _load(config.models_dir / "ml_model_p5_priority.pkl", "P5")
    if data is None:
        return None
    return {"model": data["model"], "labels": data.get("labels", [])}

@lru_cache(maxsize=1)
def load_p6():
    data = _load(config.models_dir / "ml_model_p6_schedule.pkl", "P6")
    return _extract(data)

def startup_check():
    """Call at service startup. Logs status of all models."""
    for name, fn in [("P1", load_p1), ("P2", load_p2), ("P3", load_p3),
                     ("P4", load_p4), ("P5", load_p5), ("P6", load_p6)]:
        result = fn()
        status = "OK" if result is not None else "MISSING"
        logger.info(f"[{status}] {name} model")
```

Replaces: `global _MODEL` pattern (P1), module-level eager loads (P2–P6), scattered `try/except joblib.load` blocks.

---

### `core/feature_validator.py`

Direct rename of `feature_store.py`. Move to `core/`, update all imports. No logic changes.

---

## Data Flow

```
HTTP Request
    │
    ▼
api/routes.py  (Sub-2)
    │  builds SensorReading from request body
    ▼
core/feature_validator.py
    │  validates sensor ranges — HTTP 422 on bad input
    ▼
core/feature_pipeline.py
    │  build_5() or build_7() — one place, no duplication
    ▼
core/model_loader.py
    │  load_pN() — lazy, cached, never crashes
    ▼
inference/[model].py  (Sub-2) / predictions.py (Sub-1 interim)
    │  model.predict() on clean features
    ▼
JSON response
```

---

## Error Handling

| Failure | Where caught | Behavior |
|---------|-------------|----------|
| pkl file missing | `model_loader._load()` | Log ERROR, return `None`. Caller returns safe default. Never crashes startup. |
| Bad sensor input | `feature_validator.py` | Raise `ValueError` with field + allowed range. Router → HTTP 422. |
| Inference exception | Each prediction method | Log WARNING + traceback. Return safe default (0.0 / {}). Never HTTP 500. |

**Rule:** missing model = degraded mode (other models still serve). Bad input = reject at boundary. Inference error = safe default + log.

---

## Files Changed in Sub-1

| File | Change | Risk |
|------|--------|------|
| `core/config.py` | NEW | — |
| `core/feature_pipeline.py` | NEW | — |
| `core/model_loader.py` | NEW (refactor of existing) | Low |
| `core/feature_validator.py` | RENAME from `feature_store.py` | Low — update imports |
| `predictions.py` | Replace inline derivation with `FeaturePipeline` calls | Low — ~30 lines |
| `router.py` | Import thresholds from `config` | Low — ~15 lines |
| `dst_fusion.py` | Import `config.dst_conflict_threshold` | Low — ~5 lines |

**Zero behavior changes.** Pure structural cleanup.

---

## Testing

```
tests/
  unit/
    core/
      test_config.py             ← env override, defaults, models_dir resolves
      test_feature_pipeline.py   ← build_5/7 correctness, zero values, edge cases
      test_feature_validator.py  ← bad ranges rejected, good ranges pass
      test_model_loader.py       ← missing file → None, cache hit, corrupt pkl
  integration/
    test_predictions_pipeline.py ← raw input → prediction (real pkl)
```

**Key cases:**
- `build_7()` derives `temp_delta` and `rpm_torque` correctly
- `load_p1()` with missing file → `None`, no exception
- Second call to `load_p1()` hits `lru_cache` (not disk)
- `ML_P4_ANOMALY_THRESHOLD=0.7` env var overrides default `0.5`
- Bad input (RPM = -1) → HTTP 422 before model is called
- All 6 models missing → service starts, all endpoints return safe defaults

No mocking of sklearn internals. No performance tests (Sub-4 scope).

---

## Success Criteria

- [ ] `temp_delta` / `rpm_torque` computed in exactly one place
- [ ] All 6 model loaders use `@lru_cache` + `_extract()` pattern
- [ ] All threshold literals removed from `router.py`, `dst_fusion.py`, `predictions.py`
- [ ] Missing any/all pkl files → service starts cleanly, logs MISSING, serves defaults
- [ ] All existing prediction behavior unchanged (integration tests pass)
- [ ] Every new file has sibling `.md` readable by non-ML engineer
