# Shared Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `app/ml-microservice/src/core/` with unified config, feature pipeline, and model loader — eliminating 6× duplicated feature derivation, mixed loader patterns, and hardcoded thresholds across `predictions.py`, `router.py`, and `dst_fusion.py`.

**Architecture:** Three new modules in `core/` (config, feature_pipeline, model_loader) + rename of `feature_store.py` → `core/feature_validator.py`. Existing files (`predictions.py`, `router.py`, `dst_fusion.py`) are touched minimally to import from `core/`. Zero behavior changes — pure structural cleanup.

**Tech Stack:** Python 3.10+, FastAPI, pydantic-settings 2.x, joblib, functools.lru_cache

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/core/__init__.py` | CREATE | Package marker |
| `src/core/config.py` | CREATE | All ML params, thresholds, paths — Pydantic BaseSettings |
| `src/core/config.md` | CREATE | Plain-English explanation |
| `src/core/feature_pipeline.py` | CREATE | `build_5()` / `build_7()` — single source of feature derivation |
| `src/core/feature_pipeline.md` | CREATE | Plain-English explanation |
| `src/core/model_loader.py` | CREATE | Uniform lazy-load via `@lru_cache` for P1–P6 |
| `src/core/model_loader.md` | CREATE | Plain-English explanation |
| `src/core/feature_validator.py` | CREATE (rename) | Input validation + ranges — moved from `feature_store.py` |
| `src/core/feature_validator.md` | CREATE | Plain-English explanation |
| `src/feature_store.py` | DELETE | Replaced by `core/feature_validator.py` |
| `src/model_loader.py` | DELETE | Replaced by `core/model_loader.py` |
| `src/predictions.py` | MODIFY | Import from `core/`, remove inline derivation, use config thresholds |
| `src/router.py` | MODIFY | Import config + FeaturePipeline from `core/`, remove inline derivation |
| `src/dst_fusion.py` | MODIFY | Import `config.dst_conflict_threshold`, remove hardcoded `0.8` |
| `requirements.txt` | MODIFY | Add `pydantic-settings>=2.0.0` |
| `tests/unit/core/test_config.py` | CREATE | Unit tests for config |
| `tests/unit/core/test_feature_pipeline.py` | CREATE | Unit tests for feature pipeline |
| `tests/unit/core/test_model_loader.py` | CREATE | Unit tests for model loader |
| `tests/unit/core/test_feature_validator.py` | CREATE | Unit tests for feature validator |
| `tests/integration/test_predictions_pipeline.py` | CREATE | End-to-end inference tests |

---

## Task 1: Add pydantic-settings + scaffold core/ package

**Files:**
- Modify: `app/ml-microservice/requirements.txt`
- Create: `app/ml-microservice/src/core/__init__.py`
- Create: `tests/unit/core/__init__.py`

- [ ] **Step 1: Add pydantic-settings to requirements**

Open `app/ml-microservice/requirements.txt`. Add after the pydantic line:

```
pydantic-settings>=2.0.0
```

Full file after edit:
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
joblib>=1.3.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
psutil>=5.9.0
pykalman>=0.9.7
```

- [ ] **Step 2: Create core/ package**

```bash
mkdir -p app/ml-microservice/src/core
touch app/ml-microservice/src/core/__init__.py
mkdir -p tests/unit/core
touch tests/unit/core/__init__.py
touch tests/unit/__init__.py
```

- [ ] **Step 3: Commit**

```bash
git add app/ml-microservice/requirements.txt app/ml-microservice/src/core/__init__.py tests/unit/core/__init__.py tests/unit/__init__.py
git commit -m "chore: scaffold core/ package + add pydantic-settings dependency"
```

---

## Task 2: core/config.py — centralized settings

**Files:**
- Create: `app/ml-microservice/src/core/config.py`
- Create: `tests/unit/core/test_config.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/core/test_config.py`:

```python
import os
import pytest
from pathlib import Path


def test_default_p4_anomaly_threshold():
    from app.ml_microservice.src.core.config import MLConfig
    cfg = MLConfig()
    assert cfg.p4_anomaly_threshold == 0.5


def test_default_dst_conflict_threshold():
    from app.ml_microservice.src.core.config import MLConfig
    cfg = MLConfig()
    assert cfg.dst_conflict_threshold == 0.8


def test_default_risk_thresholds():
    from app.ml_microservice.src.core.config import MLConfig
    cfg = MLConfig()
    assert cfg.p1_risk_medium == 25.0
    assert cfg.p1_risk_high == 50.0
    assert cfg.p1_risk_critical == 75.0


def test_env_override_p4_threshold(monkeypatch):
    monkeypatch.setenv("ML_P4_ANOMALY_THRESHOLD", "0.7")
    # Force re-instantiation by importing the class directly
    from app.ml_microservice.src.core.config import MLConfig
    cfg = MLConfig()
    assert cfg.p4_anomaly_threshold == 0.7


def test_models_dir_is_absolute():
    from app.ml_microservice.src.core.config import MLConfig
    cfg = MLConfig()
    assert cfg.models_dir.is_absolute()


def test_default_feature_values():
    from app.ml_microservice.src.core.config import MLConfig
    cfg = MLConfig()
    assert cfg.default_air_temp == 298.0
    assert cfg.default_process_temp == 308.0
    assert cfg.default_rpm == 1500
    assert cfg.default_torque == 40.0
    assert cfg.default_tool_wear == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd app/ml-microservice && python -m pytest ../../tests/unit/core/test_config.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` — `core/config.py` does not exist yet.

- [ ] **Step 3: Implement core/config.py**

Create `app/ml-microservice/src/core/config.py`:

```python
from pathlib import Path
from pydantic_settings import BaseSettings


class MLConfig(BaseSettings):
    # Model file paths base directory
    models_dir: Path = Path(__file__).parent.parent.parent / "models"

    # P1 — failure probability risk level thresholds (%)
    p1_risk_medium: float = 25.0
    p1_risk_high: float = 50.0
    p1_risk_critical: float = 75.0

    # P4 — anomaly detection score threshold (0.0–1.0)
    p4_anomaly_threshold: float = 0.5

    # Wave 2 DST fusion — Dempster-Shafer conflict threshold
    dst_conflict_threshold: float = 0.8

    # Sensor defaults — used when a reading is missing from the request
    default_air_temp: float = 298.0
    default_process_temp: float = 308.0
    default_rpm: int = 1500
    default_torque: float = 40.0
    default_tool_wear: int = 0

    model_config = {"env_prefix": "ML_"}


config = MLConfig()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd app/ml-microservice && python -m pytest ../../tests/unit/core/test_config.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/ml-microservice/src/core/config.py tests/unit/core/test_config.py
git commit -m "feat(core): add MLConfig with Pydantic BaseSettings for all ML parameters"
```

---

## Task 3: core/feature_pipeline.py — single feature derivation source

**Files:**
- Create: `app/ml-microservice/src/core/feature_pipeline.py`
- Create: `tests/unit/core/test_feature_pipeline.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/core/test_feature_pipeline.py`:

```python
import pytest
from app.ml_microservice.src.core.feature_pipeline import FeaturePipeline, SensorReading


@pytest.fixture
def reading():
    return SensorReading(
        air_temp=298.0,
        process_temp=308.0,
        rpm=1500.0,
        torque=40.0,
        tool_wear=10.0,
    )


def test_build_5_returns_five_values(reading):
    result = FeaturePipeline.build_5(reading)
    assert len(result) == 5


def test_build_5_correct_order(reading):
    result = FeaturePipeline.build_5(reading)
    assert result == [298.0, 308.0, 1500.0, 40.0, 10.0]


def test_build_7_returns_seven_values(reading):
    result = FeaturePipeline.build_7(reading)
    assert len(result) == 7


def test_build_7_temp_delta_correct(reading):
    result = FeaturePipeline.build_7(reading)
    # temp_delta = process_temp - air_temp = 308.0 - 298.0 = 10.0
    assert result[5] == pytest.approx(10.0)


def test_build_7_rpm_torque_correct(reading):
    result = FeaturePipeline.build_7(reading)
    # rpm_torque = (rpm * torque) / 1000 = (1500 * 40) / 1000 = 60.0
    assert result[6] == pytest.approx(60.0)


def test_build_7_first_five_match_build_5(reading):
    result_5 = FeaturePipeline.build_5(reading)
    result_7 = FeaturePipeline.build_7(reading)
    assert result_7[:5] == result_5


def test_build_5_zero_tool_wear():
    r = SensorReading(air_temp=300.0, process_temp=310.0, rpm=1000.0, torque=30.0, tool_wear=0.0)
    result = FeaturePipeline.build_5(r)
    assert result[4] == 0.0


def test_build_7_zero_rpm_torque_product():
    r = SensorReading(air_temp=300.0, process_temp=310.0, rpm=0.0, torque=40.0, tool_wear=5.0)
    result = FeaturePipeline.build_7(r)
    assert result[6] == pytest.approx(0.0)


def test_build_7_negative_temp_delta():
    # process_temp < air_temp is unusual but should not crash
    r = SensorReading(air_temp=310.0, process_temp=300.0, rpm=1500.0, torque=40.0, tool_wear=5.0)
    result = FeaturePipeline.build_7(r)
    assert result[5] == pytest.approx(-10.0)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd app/ml-microservice && python -m pytest ../../tests/unit/core/test_feature_pipeline.py -v
```

Expected: `ImportError` — module does not exist yet.

- [ ] **Step 3: Implement core/feature_pipeline.py**

Create `app/ml-microservice/src/core/feature_pipeline.py`:

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
        """5 raw sensor features: [air, process, rpm, torque, wear]. Used by P3, P4."""
        return [r.air_temp, r.process_temp, r.rpm, r.torque, r.tool_wear]

    @staticmethod
    def build_7(r: SensorReading) -> List[float]:
        """7 features: 5 raw + temp_delta + rpm_torque. Used by P1, P2, P5, P6."""
        temp_delta = r.process_temp - r.air_temp
        rpm_torque = (r.rpm * r.torque) / 1000.0
        return [r.air_temp, r.process_temp, r.rpm, r.torque, r.tool_wear,
                temp_delta, rpm_torque]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd app/ml-microservice && python -m pytest ../../tests/unit/core/test_feature_pipeline.py -v
```

Expected: all 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/ml-microservice/src/core/feature_pipeline.py tests/unit/core/test_feature_pipeline.py
git commit -m "feat(core): add FeaturePipeline with build_5/build_7 — single derivation source"
```

---

## Task 4: core/model_loader.py — uniform lazy-load

**Files:**
- Create: `app/ml-microservice/src/core/model_loader.py`
- Create: `tests/unit/core/test_model_loader.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/core/test_model_loader.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


def _reset_cache():
    """Clear lru_cache between tests so each test starts fresh."""
    from app.ml_microservice.src.core import model_loader as ml
    ml.load_p1.cache_clear()
    ml.load_p2.cache_clear()
    ml.load_p3.cache_clear()
    ml.load_p4.cache_clear()
    ml.load_p5.cache_clear()
    ml.load_p6.cache_clear()


def test_missing_pkl_returns_none(tmp_path):
    _reset_cache()
    from app.ml_microservice.src.core.model_loader import _load
    result = _load(tmp_path / "nonexistent.pkl", "TEST")
    assert result is None


def test_missing_pkl_does_not_raise(tmp_path):
    _reset_cache()
    from app.ml_microservice.src.core.model_loader import _load
    # Must not raise — returns None silently
    result = _load(tmp_path / "missing.pkl", "TEST")
    assert result is None


def test_extract_dict_with_model_key():
    from app.ml_microservice.src.core.model_loader import _extract
    fake_model = MagicMock()
    data = {"model": fake_model, "features": ["a", "b"]}
    assert _extract(data) is fake_model


def test_extract_bare_model_fallback():
    from app.ml_microservice.src.core.model_loader import _extract
    bare = MagicMock()
    assert _extract(bare) is bare


def test_load_p1_missing_returns_none(tmp_path, monkeypatch):
    _reset_cache()
    from app.ml_microservice.src.core import model_loader as ml
    monkeypatch.setattr(ml.config, "models_dir", tmp_path)
    result = ml.load_p1()
    assert result is None


def test_load_p1_cache_hit_skips_disk(tmp_path, monkeypatch):
    _reset_cache()
    from app.ml_microservice.src.core import model_loader as ml
    monkeypatch.setattr(ml.config, "models_dir", tmp_path)
    # Call twice — both return None but only one disk hit
    with patch.object(ml, "_load", wraps=ml._load) as mock_load:
        ml.load_p1()
        ml.load_p1()
        # _load called only once thanks to lru_cache
        assert mock_load.call_count == 1


def test_startup_check_runs_without_exception(tmp_path, monkeypatch):
    _reset_cache()
    from app.ml_microservice.src.core import model_loader as ml
    monkeypatch.setattr(ml.config, "models_dir", tmp_path)
    # All models missing — startup_check must not raise
    ml.startup_check()


def test_load_p4_missing_returns_none(tmp_path, monkeypatch):
    _reset_cache()
    from app.ml_microservice.src.core import model_loader as ml
    monkeypatch.setattr(ml.config, "models_dir", tmp_path)
    result = ml.load_p4()
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd app/ml-microservice && python -m pytest ../../tests/unit/core/test_model_loader.py -v
```

Expected: `ImportError` — module does not exist yet.

- [ ] **Step 3: Implement core/model_loader.py**

Create `app/ml-microservice/src/core/model_loader.py`:

```python
import logging
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import joblib

from .config import config

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

logger = logging.getLogger(__name__)


def _extract(data: Any, key: str = "model") -> Any:
    """Return data[key] if dict, else return data (legacy bare-model pkls)."""
    if isinstance(data, dict):
        return data.get(key)
    return data


def _load(path: Path, label: str) -> Optional[Any]:
    """Load a pkl file safely. Returns None on any failure — never raises."""
    if not path.exists():
        logger.error(f"[MISSING] {label} pkl not found: {path}")
        return None
    try:
        return joblib.load(path)
    except Exception as e:
        logger.error(f"[ERROR] {label} pkl failed to load: {e}")
        return None


@lru_cache(maxsize=1)
def load_p1() -> Optional[Any]:
    data = _load(config.models_dir / "basic_machine_model.pkl", "P1")
    return _extract(data)


@lru_cache(maxsize=1)
def load_p2() -> Optional[dict]:
    data = _load(config.models_dir / "ml_model_p2_failure_type.pkl", "P2")
    if data is None:
        return None
    return {
        "model":  data["model"],
        "labels": data.get("labels", []),
    }


@lru_cache(maxsize=1)
def load_p3() -> Optional[Any]:
    data = _load(config.models_dir / "ml_model_p3_rul.pkl", "P3")
    return _extract(data)


@lru_cache(maxsize=1)
def load_p4() -> Optional[dict]:
    v2 = config.models_dir / "ml_model_p4_anomaly_v2.pkl"
    v1 = config.models_dir / "ml_model_p4_anomaly.pkl"
    path = v2 if v2.exists() else v1
    data = _load(path, "P4")
    if data is None:
        return None
    if isinstance(data, dict) and "iso_model" in data:
        result = {
            "model":          data["iso_model"],
            "weights":        data.get("weights", {"ae": 0.40, "if": 0.30, "zscore": 0.20, "cluster": 0.10}),
            "thresholds":     data.get("thresholds", {}),
            "training_stats": data.get("training_stats", {}),
            "ae_scaler":      data.get("ae_scaler"),
            "autoencoder":    None,
            "feature_pipeline": None,
            "ensemble_type":  data.get("type", "anomaly_ensemble_v2"),
        }
        # Optional autoencoder (requires TensorFlow)
        ae_path = data.get("autoencoder_path")
        if ae_path and Path(ae_path).exists():
            try:
                import tensorflow as tf  # noqa: F401
                result["autoencoder"] = tf.keras.models.load_model(ae_path)
                logger.info("[OK] P4 autoencoder loaded")
            except ImportError:
                logger.info("[INFO] P4 autoencoder skipped — TensorFlow not installed")
            except Exception as e:
                logger.warning(f"[WARN] P4 autoencoder failed: {e}")
        # Optional cluster feature pipeline
        pipeline_path = config.models_dir / "feature_pipeline_v3.pkl"
        if pipeline_path.exists():
            try:
                result["feature_pipeline"] = joblib.load(pipeline_path)
                logger.info("[OK] P4 feature pipeline loaded")
            except Exception as e:
                logger.warning(f"[WARN] P4 feature pipeline failed: {e}")
        logger.info(f"[OK] P4 ensemble loaded (type={result['ensemble_type']})")
        return result
    # Legacy bare IF model
    logger.info("[OK] P4 legacy IF loaded")
    return {"model": _extract(data), "weights": {}, "thresholds": {}, "training_stats": {},
            "ae_scaler": None, "autoencoder": None, "feature_pipeline": None,
            "ensemble_type": "isolation_forest"}


@lru_cache(maxsize=1)
def load_p5() -> Optional[dict]:
    data = _load(config.models_dir / "ml_model_p5_priority.pkl", "P5")
    if data is None:
        return None
    return {
        "model":  data["model"],
        "labels": data.get("labels", []),
    }


@lru_cache(maxsize=1)
def load_p6() -> Optional[Any]:
    data = _load(config.models_dir / "ml_model_p6_schedule.pkl", "P6")
    return _extract(data)


def get_all_models_status() -> dict:
    """Return load status of all models. Called by /health endpoint."""
    p4 = load_p4()
    return {
        "p1_failure":      {"loaded": load_p1() is not None},
        "p2_failure_type": {"loaded": load_p2() is not None},
        "p3_rul":          {"loaded": load_p3() is not None},
        "p4_anomaly": {
            "loaded":      p4 is not None,
            "type":        p4["ensemble_type"] if p4 else "unknown",
            "autoencoder": bool(p4 and p4.get("autoencoder")),
            "cluster":     bool(p4 and p4.get("feature_pipeline")),
        },
        "p5_priority":     {"loaded": load_p5() is not None},
        "p6_schedule":     {"loaded": load_p6() is not None},
    }


def startup_check() -> None:
    """Call at service startup. Logs OK/MISSING for every model."""
    for name, fn in [("P1", load_p1), ("P2", load_p2), ("P3", load_p3),
                     ("P4", load_p4), ("P5", load_p5), ("P6", load_p6)]:
        result = fn()
        logger.info(f"[{'OK' if result is not None else 'MISSING'}] {name} model")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd app/ml-microservice && python -m pytest ../../tests/unit/core/test_model_loader.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/ml-microservice/src/core/model_loader.py tests/unit/core/test_model_loader.py
git commit -m "feat(core): add uniform model loader with lru_cache for P1-P6"
```

---

## Task 5: core/feature_validator.py — move from feature_store.py

**Files:**
- Create: `app/ml-microservice/src/core/feature_validator.py` (content from `feature_store.py`)
- Create: `tests/unit/core/test_feature_validator.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/core/test_feature_validator.py`:

```python
import pytest
from app.ml_microservice.src.core.feature_validator import FeatureValidator


def test_valid_sensor_passes():
    telemetry = {
        "air_temperature": 298.0,
        "process_temperature": 308.0,
        "rotational_speed": 1500,
        "torque": 40.0,
        "tool_wear": 10,
    }
    # Should not raise
    FeatureValidator.validate(telemetry)


def test_negative_rpm_raises():
    telemetry = {
        "air_temperature": 298.0,
        "process_temperature": 308.0,
        "rotational_speed": -1,
        "torque": 40.0,
        "tool_wear": 10,
    }
    with pytest.raises(ValueError, match="rotational_speed"):
        FeatureValidator.validate(telemetry)


def test_zero_tool_wear_is_valid():
    telemetry = {
        "air_temperature": 298.0,
        "process_temperature": 308.0,
        "rotational_speed": 1500,
        "torque": 40.0,
        "tool_wear": 0,
    }
    FeatureValidator.validate(telemetry)


def test_extreme_tool_wear_raises():
    telemetry = {
        "air_temperature": 298.0,
        "process_temperature": 308.0,
        "rotational_speed": 1500,
        "torque": 40.0,
        "tool_wear": 9999,
    }
    with pytest.raises(ValueError, match="tool_wear"):
        FeatureValidator.validate(telemetry)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd app/ml-microservice && python -m pytest ../../tests/unit/core/test_feature_validator.py -v
```

Expected: `ImportError` — module does not exist yet.

- [ ] **Step 3: Create core/feature_validator.py**

Create `app/ml-microservice/src/core/feature_validator.py` with the content of the existing `feature_store.py`, renaming the class from `FeatureStore` to `FeatureValidator` and the instance from `feature_store` to `feature_validator`. Add the `validate()` classmethod used by tests:

```python
"""
Feature Validator
Validates and extracts features from raw sensor telemetry dicts.
Moved from feature_store.py — same logic, clearer name.
"""
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class FeatureValidator:
    """Validate sensor readings and extract feature vectors."""

    RANGES = {
        'air_temperature':    (0, 2000),
        'process_temperature': (0, 5000),
        'rotational_speed':   (0, 10000),
        'torque':             (0, 1000),
        'tool_wear':          (0, 300),
    }

    DEFAULTS = {
        'air_temperature':    298,
        'process_temperature': 308,
        'rotational_speed':   1500,
        'torque':             40,
        'tool_wear':          0,
    }

    @classmethod
    def validate(cls, telemetry: Dict) -> None:
        """Raise ValueError if any sensor reading is outside allowed range."""
        for field, (lo, hi) in cls.RANGES.items():
            if field in telemetry:
                val = float(telemetry[field])
                if not (lo <= val <= hi):
                    raise ValueError(
                        f"{field}={val} out of range [{lo}, {hi}]"
                    )

    @staticmethod
    def extract_5_features(telemetry: Dict) -> List[float]:
        return [
            float(telemetry.get('air_temperature', 298)),
            float(telemetry.get('process_temperature', 308)),
            int(telemetry.get('rotational_speed', 1500)),
            float(telemetry.get('torque', 40)),
            int(telemetry.get('tool_wear', 0)),
        ]

    @staticmethod
    def extract_full_snapshot(telemetry: Dict, context: Optional[Dict] = None) -> Dict:
        """Delegate to existing FeatureStore logic — copied verbatim to preserve behavior."""
        # Import original for full snapshot logic (removed in Sub-2 cleanup)
        from ..feature_store import FeatureStore
        return FeatureStore.extract_full_snapshot(telemetry, context)

    @staticmethod
    def build_time_series_from_logs(machine_id: int, logs: list) -> list:
        from ..feature_store import FeatureStore
        return FeatureStore.build_time_series_from_logs(machine_id, logs)


# Module-level instance — backward compatible with existing `from .feature_validator import feature_validator`
feature_validator = FeatureValidator()
```

**Note:** `extract_full_snapshot` and `build_time_series_from_logs` delegate to the original `feature_store.py` temporarily. `feature_store.py` is NOT deleted yet — Sub-2 will complete the migration when `predictions.py` is fully refactored.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd app/ml-microservice && python -m pytest ../../tests/unit/core/test_feature_validator.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/ml-microservice/src/core/feature_validator.py tests/unit/core/test_feature_validator.py
git commit -m "feat(core): add FeatureValidator (moved from feature_store.py)"
```

---

## Task 6: Update predictions.py — use core/ imports

**Files:**
- Modify: `app/ml-microservice/src/predictions.py`

Changes: replace private globals from old `model_loader` with `load_pN()` calls; replace inline `temp_delta`/`rpm_torque` derivation in `get_all_predictions` with `FeaturePipeline`; replace hardcoded `0.5` threshold with `config.p4_anomaly_threshold`.

- [ ] **Step 1: Update the import block**

Replace lines 1–31 of `predictions.py`:

```python
"""
ML Predictions Service
Provides P1-P6 prediction methods + DST unified health fusion (Wave 2).
"""
import logging
import numpy as np
from typing import List, Dict, Optional

from .core.config import config
from .core.feature_pipeline import FeaturePipeline, SensorReading
from .core.model_loader import load_p1, load_p2, load_p3, load_p4, load_p5, load_p6
from .feature_store import FeatureStore
from .health_index import MahalanobisHealthIndex, get_health_index_model
from .survival_model import SurvivalModel, get_survival_model
from .anomaly_cusum import AnomalyEnsemble, get_anomaly_ensemble
from .kalman_estimator import KalmanStateEstimator, get_kalman_estimator
from .dst_fusion import DSTFusion, get_dst_fusion

logger = logging.getLogger(__name__)

try:
    from .pinn_rul import PINNRULEstimator, get_pinn_estimator
    _PINN_AVAILABLE = True
except ImportError:
    _PINN_AVAILABLE = False
    get_pinn_estimator = None

try:
    from .moment_estimator import (
        get_moment_anomaly_detector,
        get_moment_rul_estimator,
        MOMENT_AVAILABLE as _MOMENT_AVAILABLE,
    )
except ImportError:
    _MOMENT_AVAILABLE = False
    get_moment_anomaly_detector = None
    get_moment_rul_estimator = None
```

- [ ] **Step 2: Update predict_failure_probability (P1)**

Find `def predict_failure_probability` (around line 67). Replace the method body:

```python
    @staticmethod
    def predict_failure_probability(features: List[float]) -> float:
        model_p1 = load_p1()
        if model_p1 is None:
            return 0.0
        try:
            features_7 = features[:7] if len(features) >= 7 else features
            prob = model_p1.predict_proba([features_7])[0, 1]
            return round(prob * 100, 1)
        except Exception:
            logger.warning("P1 failure probability prediction failed", exc_info=True)
            return 0.0
```

- [ ] **Step 3: Update predict_failure_type (P2)**

Find `def predict_failure_type`. Replace method body:

```python
    @staticmethod
    def predict_failure_type(features: List[float]) -> Dict:
        p2 = load_p2()
        if p2 is None:
            return {}
        model, labels = p2["model"], p2["labels"]
        try:
            input_data = [features]
            predictions = model.predict(input_data)[0]
            probabilities = [est.predict_proba(input_data)[0, 1] for est in model.estimators_]
            return {
                label: {"detected": bool(predictions[i]), "probability": round(float(probabilities[i]) * 100, 1)}
                for i, label in enumerate(labels)
            }
        except Exception:
            logger.warning("P2 failure type prediction failed", exc_info=True)
            return {}
```

- [ ] **Step 4: Update predict_rul (P3)**

Find `def predict_rul`. Replace method body:

```python
    @staticmethod
    def predict_rul(features: List[float]) -> Optional[float]:
        model_p3 = load_p3()
        if model_p3 is None:
            return None
        try:
            pred_rul = model_p3.predict(np.array([features[:7]]))[0]
            return float(pred_rul)
        except Exception:
            logger.warning("P3 RUL prediction failed", exc_info=True)
            return None
```

- [ ] **Step 5: Update detect_anomaly (P4) — replace threshold hardcode**

Find `is_anomaly = ensemble_score > 0.5` (around line 257). Replace with:

```python
            is_anomaly = ensemble_score > config.p4_anomaly_threshold
```

Also replace the P4 model access. Find the start of `detect_anomaly` and replace the model access block:

```python
    @staticmethod
    def detect_anomaly(features: List[float]) -> tuple:
        p4 = load_p4()
        if p4 is None or p4.get("model") is None:
            return False, 0.0

        _ml_model_p4 = p4["model"]
        _p4_weights = p4["weights"]
        _p4_thresholds = p4["thresholds"]
        _p4_training_stats = p4["training_stats"]
        _p4_ae_scaler = p4["ae_scaler"]
        _p4_autoencoder = p4["autoencoder"]
        _p4_feature_pipeline = p4["feature_pipeline"]
```

Keep the rest of the detect_anomaly body unchanged — it already uses these local variable names.

- [ ] **Step 6: Update predict_priority (P5)**

Find `def predict_priority`. Replace model access at the top of the method body:

```python
    @staticmethod
    def predict_priority(features: List[float]) -> str:
        p5 = load_p5()
        if p5 is None:
            return "MEDIUM"
        model, labels = p5["model"], p5["labels"]
```

Keep the rest of the method body unchanged but replace all `_ml_model_p5` → `model` and `_p5_labels` → `labels`.

- [ ] **Step 7: Update predict_maintenance_schedule (P6)**

Find `def predict_maintenance_schedule`. Replace model access:

```python
    @staticmethod
    def predict_maintenance_schedule(features: List[float]) -> float:
        model_p6 = load_p6()
        if model_p6 is None:
            return 30.0
```

Replace all `_ml_model_p6` → `model_p6` in the method body.

- [ ] **Step 8: Update get_all_predictions — use FeaturePipeline**

Find `get_all_predictions` method (around line 330). Replace the feature extraction block (lines 342–357):

```python
        air   = float(telemetry.get("air_temperature",    config.default_air_temp))
        process = float(telemetry.get("process_temperature", config.default_process_temp))
        rpm   = float(telemetry.get("rotational_speed",   config.default_rpm))
        torque = float(telemetry.get("torque",            config.default_torque))
        wear  = float(telemetry.get("tool_wear",          config.default_tool_wear))

        reading = SensorReading(air_temp=air, process_temp=process,
                                rpm=rpm, torque=torque, tool_wear=wear)
        features_5 = FeaturePipeline.build_5(reading)
        features_7 = FeaturePipeline.build_7(reading)
        features_6 = features_7[:6]   # 5 raw + temp_delta (no rpm_torque)
```

- [ ] **Step 9: Verify predictions.py still imports cleanly**

```bash
cd app/ml-microservice && python -c "from src.predictions import MachineLearningService; print('OK')"
```

Expected: `OK`

- [ ] **Step 10: Commit**

```bash
git add app/ml-microservice/src/predictions.py
git commit -m "refactor(predictions): import from core/, use FeaturePipeline + config thresholds"
```

---

## Task 7: Update router.py — use config + FeaturePipeline

**Files:**
- Modify: `app/ml-microservice/src/router.py`

- [ ] **Step 1: Update imports in router.py**

Find the existing imports at top of `router.py`. Add after existing imports:

```python
from .core.config import config
from .core.feature_pipeline import FeaturePipeline, SensorReading
```

- [ ] **Step 2: Replace inline feature derivation in router.py**

There are multiple places in `router.py` that compute `temp_delta` and build feature vectors (around lines 238–239, 258, 402–403, 421, 457–458, 476). For each occurrence, replace the inline derivation block.

**Pattern to find (repeated ~4 times):**
```python
temp_delta = process - air
features = [float(air), float(process), float(rpm), float(torque), float(wear), float(temp_delta)]
```

**Replace each with:**
```python
_reading = SensorReading(air_temp=float(air), process_temp=float(process),
                         rpm=float(rpm), torque=float(torque), tool_wear=float(wear))
features = FeaturePipeline.build_7(_reading)
```

Also find similar blocks that compute `temp_delta` as part of building a features dict and replace with the same pattern. Use `build_5(_reading)` where only 5 features were being built.

- [ ] **Step 3: Verify router.py imports cleanly**

```bash
cd app/ml-microservice && python -c "from src.router import router; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add app/ml-microservice/src/router.py
git commit -m "refactor(router): use FeaturePipeline + config — remove inline feature derivation"
```

---

## Task 8: Update dst_fusion.py — use config threshold

**Files:**
- Modify: `app/ml-microservice/src/dst_fusion.py`

- [ ] **Step 1: Add config import**

Open `app/ml-microservice/src/dst_fusion.py`. After the existing imports (after line ~14), add:

```python
from .core.config import config
```

- [ ] **Step 2: Replace CONFLICT_THRESHOLD constant**

Find line 26:
```python
CONFLICT_THRESHOLD = 0.8
```

Replace with:
```python
CONFLICT_THRESHOLD = config.dst_conflict_threshold
```

This keeps the module-level constant name intact (used in `logger.warning` strings and comparisons) but sources its value from config.

- [ ] **Step 3: Verify dst_fusion.py imports cleanly**

```bash
cd app/ml-microservice && python -c "from src.dst_fusion import DSTFusion; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add app/ml-microservice/src/dst_fusion.py
git commit -m "refactor(dst_fusion): source CONFLICT_THRESHOLD from core config"
```

---

## Task 9: Wire startup_check + update old model_loader references

**Files:**
- Modify: `app/ml-microservice/src/router.py` (update `get_all_models_status` import)

- [ ] **Step 1: Update model status import in router.py**

Find in `router.py`:
```python
from .model_loader import get_all_models_status
```

Replace with:
```python
from .core.model_loader import get_all_models_status, startup_check
```

- [ ] **Step 2: Find main app entry point**

```bash
find app/ml-microservice -name "main.py" -o -name "app.py" | head -5
```

- [ ] **Step 3: Add startup_check call**

In the main FastAPI app file, find the `@app.on_event("startup")` handler or `lifespan` context. Add:

```python
from src.core.model_loader import startup_check

@app.on_event("startup")
async def startup():
    startup_check()
```

If a lifespan handler already exists, add `startup_check()` at the top of its startup block.

- [ ] **Step 4: Verify full app starts**

```bash
cd app/ml-microservice && python -m uvicorn src.router:router --port 8001 --no-access-log &
sleep 3 && curl -s http://localhost:8001/api/v1/ml/health | python -m json.tool
kill %1
```

Expected: JSON response with model status.

- [ ] **Step 5: Commit**

```bash
git add app/ml-microservice/src/router.py
git commit -m "feat(startup): wire startup_check() — logs OK/MISSING for all models at boot"
```

---

## Task 10: Integration test

**Files:**
- Create: `tests/integration/test_predictions_pipeline.py`

- [ ] **Step 1: Create integration test**

Create `tests/integration/__init__.py` and `tests/integration/test_predictions_pipeline.py`:

```python
"""
Integration tests: raw telemetry → prediction output.
Requires real .pkl files to be present. Skipped if models missing.
"""
import pytest

TELEMETRY = {
    "air_temperature": 298.1,
    "process_temperature": 308.7,
    "rotational_speed": 1551,
    "torque": 42.8,
    "tool_wear": 108,
    "machine_id": 1,
}


def _has_models():
    from app.ml_microservice.src.core.model_loader import load_p1
    return load_p1() is not None


skip_no_models = pytest.mark.skipif(not _has_models(), reason="pkl models not present")


@skip_no_models
def test_p1_returns_float_0_to_100():
    from app.ml_microservice.src.core.feature_pipeline import FeaturePipeline, SensorReading
    from app.ml_microservice.src.predictions import MachineLearningService
    r = SensorReading(298.1, 308.7, 1551.0, 42.8, 108.0)
    result = MachineLearningService.predict_failure_probability(FeaturePipeline.build_7(r))
    assert 0.0 <= result <= 100.0


@skip_no_models
def test_p4_returns_bool_and_float():
    from app.ml_microservice.src.core.feature_pipeline import FeaturePipeline, SensorReading
    from app.ml_microservice.src.predictions import MachineLearningService
    r = SensorReading(298.1, 308.7, 1551.0, 42.8, 108.0)
    is_anomaly, score = MachineLearningService.detect_anomaly(FeaturePipeline.build_5(r))
    assert isinstance(is_anomaly, bool)
    assert 0.0 <= score <= 1.0


@skip_no_models
def test_get_all_predictions_has_all_keys():
    from app.ml_microservice.src.predictions import MachineLearningService
    result = MachineLearningService.get_all_predictions(TELEMETRY)
    for key in ["p1_failure_probability", "p2_failure_types", "p3_rul_days",
                "p4_is_anomaly", "p4_anomaly_score", "p5_predicted_priority", "p6_schedule_days"]:
        assert key in result, f"Missing key: {key}"


def test_missing_models_return_safe_defaults(tmp_path, monkeypatch):
    from app.ml_microservice.src.core import model_loader as ml
    monkeypatch.setattr(ml.config, "models_dir", tmp_path)
    ml.load_p1.cache_clear()
    ml.load_p4.cache_clear()
    from app.ml_microservice.src.predictions import MachineLearningService
    assert MachineLearningService.predict_failure_probability([298, 308, 1500, 40, 10, 10, 60]) == 0.0
    is_anomaly, score = MachineLearningService.detect_anomaly([298, 308, 1500, 40, 10])
    assert is_anomaly is False
    assert score == 0.0
```

- [ ] **Step 2: Run integration tests**

```bash
cd app/ml-microservice && python -m pytest ../../tests/integration/test_predictions_pipeline.py -v
```

Expected: `test_missing_models_return_safe_defaults` PASSES. Other tests skip or pass depending on pkl presence.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/__init__.py tests/integration/test_predictions_pipeline.py
git commit -m "test(integration): add predictions pipeline tests with model-missing safety checks"
```

---

## Task 11: Write .md companion files

**Files:**
- Create: `app/ml-microservice/src/core/config.md`
- Create: `app/ml-microservice/src/core/feature_pipeline.md`
- Create: `app/ml-microservice/src/core/model_loader.md`
- Create: `app/ml-microservice/src/core/feature_validator.md`

- [ ] **Step 1: Create config.md**

```markdown
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
```

- [ ] **Step 2: Create feature_pipeline.md**

```markdown
# feature_pipeline.py

## What it does
Takes raw sensor readings and turns them into the number arrays the AI models expect.

## Why it exists
Before this file, every prediction method computed the same two numbers (temperature difference, RPM×Torque) independently. That meant the same formula existed 6 times and could drift. Now it's one place.

## Inputs / Outputs
- Input: a `SensorReading` (air temp, process temp, RPM, torque, tool wear)
- Output: a list of numbers — either 5 (raw only) or 7 (raw + 2 derived values)

## Who calls it
`predictions.py` and `router.py` — everywhere a model needs to be called.

## Derived features
| Feature | Formula | Used by |
|---------|---------|---------|
| `temp_delta` | process_temp − air_temp | P1, P2, P5, P6 |
| `rpm_torque` | (RPM × torque) ÷ 1000 | P1, P2, P5, P6 |

## What breaks if this file has a bug
All model predictions receive wrong numbers. A formula error here affects all 6 models simultaneously.
```

- [ ] **Step 3: Create model_loader.md**

```markdown
# model_loader.py

## What it does
Loads the trained AI model files (.pkl) from disk into memory, once, when first needed.

## Why it exists
Previously each model had a different loading style — some loaded at startup (crashing if a file was missing), one used a global variable. Now all 6 use the same safe pattern: load on first use, cache in memory, return None if the file is missing.

## Inputs / Outputs
- Input: nothing — reads from the path in `config.models_dir`
- Output: `load_p1()` through `load_p6()` — each returns the model object, or None if not found

## Who calls it
`predictions.py` calls `load_p1()` through `load_p6()` on every prediction request (the result is cached after the first call).

## What breaks if this file has a bug
Models may not load, causing all predictions to return safe defaults (0.0 / empty). The service stays up but gives no intelligence.

## Caching
Each `load_pN()` function uses `@lru_cache` — the pkl file is read from disk exactly once per service restart.
```

- [ ] **Step 4: Create feature_validator.md**

```markdown
# feature_validator.py

## What it does
Checks that sensor readings from the frontend are within physically plausible ranges before the AI models see them.

## Why it exists
A sensor malfunction or data entry error could send -999 RPM or 50,000°C. Without validation, the models produce nonsense outputs. This file catches bad data at the entry point.

## Inputs / Outputs
- Input: a telemetry dict from the HTTP request
- Output: raises `ValueError` with a clear message if any value is out of range; returns normally if all values are valid

## Who calls it
`router.py` — before passing data to any model.

## Allowed ranges
| Sensor | Min | Max | Unit |
|--------|-----|-----|------|
| Air temperature | 0 | 2000 | K or °C |
| Process temperature | 0 | 5000 | K or °C |
| Rotational speed | 0 | 10,000 | RPM |
| Torque | 0 | 1,000 | Nm |
| Tool wear | 0 | 300 | minutes |

## What breaks if this file has a bug
Bad sensor data reaches the models, producing unreliable predictions without any warning.
```

- [ ] **Step 5: Commit all .md files**

```bash
git add app/ml-microservice/src/core/config.md app/ml-microservice/src/core/feature_pipeline.md app/ml-microservice/src/core/model_loader.md app/ml-microservice/src/core/feature_validator.md
git commit -m "docs(core): add plain-English .md companion files for all core/ modules"
```

---

## Task 12: Full test suite + final check

- [ ] **Step 1: Run all unit tests**

```bash
cd app/ml-microservice && python -m pytest ../../tests/unit/core/ -v
```

Expected: all tests PASS.

- [ ] **Step 2: Run integration tests**

```bash
cd app/ml-microservice && python -m pytest ../../tests/integration/ -v
```

Expected: safety tests PASS, model tests skip or PASS.

- [ ] **Step 3: Verify success criteria from spec**

```bash
# temp_delta / rpm_torque computed in exactly one place
grep -rn "process_temp - air\|rpm.*torque.*1000\|torque.*rpm.*1000" app/ml-microservice/src/ --include="*.py" | grep -v "core/feature_pipeline.py" | grep -v ".pyc"
```

Expected: 0 results (all derivation removed from everywhere except `core/feature_pipeline.py`).

```bash
# No hardcoded threshold literals remaining in router/dst_fusion/predictions
grep -n "= 0\.5\b\|= 0\.8\b\|= 75\.0\b\|= 50\.0\b\|= 25\.0\b" app/ml-microservice/src/router.py app/ml-microservice/src/dst_fusion.py app/ml-microservice/src/predictions.py
```

Expected: 0 matches (all replaced by `config.*`).

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat(sub1): complete shared infrastructure refactor

- core/config.py: Pydantic BaseSettings, all ML params env-overridable
- core/feature_pipeline.py: build_5/build_7, eliminates 6x duplication
- core/model_loader.py: uniform lru_cache loaders for P1-P6
- core/feature_validator.py: input validation (moved from feature_store.py)
- predictions.py, router.py, dst_fusion.py: import from core/
- .md companion files for all core/ modules
- Unit + integration tests for all new modules"
```
