import pytest
from app.ml_microservice.src.core.feature_pipeline import SensorReading, FeaturePipeline


def make_reading(air=300.0, process=310.0, rpm=1500.0, torque=40.0, wear=50.0):
    return SensorReading(air_temp=air, process_temp=process, rpm=rpm, torque=torque, tool_wear=wear)


def test_build_5_returns_5_features():
    r = make_reading()
    features = FeaturePipeline.build_5(r)
    assert len(features) == 5


def test_build_5_correct_order():
    r = make_reading(air=300.0, process=310.0, rpm=1500.0, torque=40.0, wear=50.0)
    assert FeaturePipeline.build_5(r) == [300.0, 310.0, 1500.0, 40.0, 50.0]


def test_build_7_returns_7_features():
    r = make_reading()
    features = FeaturePipeline.build_7(r)
    assert len(features) == 7


def test_build_7_temp_delta_correct():
    r = make_reading(air=300.0, process=310.0)
    features = FeaturePipeline.build_7(r)
    assert features[5] == pytest.approx(10.0)  # temp_delta = 310 - 300


def test_build_7_rpm_torque_correct():
    r = make_reading(rpm=1500.0, torque=40.0)
    features = FeaturePipeline.build_7(r)
    assert features[6] == pytest.approx(60.0)  # rpm_torque = 1500 * 40 / 1000


def test_build_7_contains_build_5_prefix():
    r = make_reading()
    f5 = FeaturePipeline.build_5(r)
    f7 = FeaturePipeline.build_7(r)
    assert f7[:5] == f5  # first 5 are identical


def test_build_7_zero_values():
    r = SensorReading(air_temp=0.0, process_temp=0.0, rpm=0.0, torque=0.0, tool_wear=0.0)
    features = FeaturePipeline.build_7(r)
    assert features == [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]


def test_build_5_zero_values():
    r = SensorReading(air_temp=0.0, process_temp=0.0, rpm=0.0, torque=0.0, tool_wear=0.0)
    assert FeaturePipeline.build_5(r) == [0.0, 0.0, 0.0, 0.0, 0.0]
