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
