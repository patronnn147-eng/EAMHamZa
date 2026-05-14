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
