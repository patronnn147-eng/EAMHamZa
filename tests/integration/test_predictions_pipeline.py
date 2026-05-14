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
def test_predict_all_has_all_keys():
    from app.ml_microservice.src.predictions import MachineLearningService
    result = MachineLearningService.predict_all(TELEMETRY)
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
