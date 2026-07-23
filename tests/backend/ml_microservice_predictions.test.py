"""
Unit coverage for app/ml-microservice/src/predictions.py — pure helper functions
and MachineLearningService static methods, using fake model objects so no real
.pkl artifacts are needed. Imported via `src.predictions` (not the flat module
name used by some sibling tests) because predictions.py uses package-relative
imports (`from .core.config import config`) that only resolve when `src` is
loaded as a package.
"""
import sys
import os
import importlib

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../app/ml-microservice'))

predictions = importlib.import_module("src.predictions")

MachineLearningService = predictions.MachineLearningService


# ---------------------------------------------------------------------------
# _detect_maintenance_event
# ---------------------------------------------------------------------------

def test_detect_maintenance_event_no_history():
    assert predictions._detect_maintenance_event([], 5.0) is False


def test_detect_maintenance_event_current_wear_too_high():
    logs = [{"tool_wear": 50.0}, {"tool_wear": 60.0}]
    assert predictions._detect_maintenance_event(logs, 15.0) is False


def test_detect_maintenance_event_detects_reset():
    logs = [{"tool_wear": 45.0}, {"tool_wear": 60.0}, {"tool_wear": 65.0}]
    assert predictions._detect_maintenance_event(logs, 2.0) is True


def test_detect_maintenance_event_no_prior_high_wear():
    logs = [{"tool_wear": 5.0}, {"tool_wear": 8.0}]
    assert predictions._detect_maintenance_event(logs, 3.0) is False


def test_detect_maintenance_event_malformed_log_entry_skipped():
    # lookback excludes the very last entry, so put the malformed one
    # ahead of a genuine high-wear reading to exercise the `continue` path.
    logs = [{"tool_wear": "not-a-number"}, {"tool_wear": 60.0}, {"tool_wear": 62.0}]
    assert predictions._detect_maintenance_event(logs, 2.0) is True


# ---------------------------------------------------------------------------
# failure_prob_to_risk
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("prob,expected", [
    (90.0, "CRITICAL"),
    (60.0, "HIGH"),
    (30.0, "MEDIUM"),
    (5.0, "LOW"),
])
def test_failure_prob_to_risk(prob, expected):
    assert predictions.failure_prob_to_risk(prob) == expected


# ---------------------------------------------------------------------------
# _safe_hi
# ---------------------------------------------------------------------------

def test_safe_hi_none_output():
    assert predictions._safe_hi(None) == 75.0


def test_safe_hi_missing_key_uses_default():
    assert predictions._safe_hi({}, default=50.0) == 50.0


def test_safe_hi_nan_value_uses_default():
    assert predictions._safe_hi({"health_index": float("nan")}, default=42.0) == 42.0


def test_safe_hi_valid_value():
    assert predictions._safe_hi({"health_index": 88.0}) == 88.0


# ---------------------------------------------------------------------------
# _parse_iso_ts
# ---------------------------------------------------------------------------

def test_parse_iso_ts_empty_string():
    assert predictions._parse_iso_ts("") is None


def test_parse_iso_ts_invalid_string():
    assert predictions._parse_iso_ts("not-a-timestamp") is None


def test_parse_iso_ts_valid_z_suffix():
    dt = predictions._parse_iso_ts("2026-07-01T12:00:00Z")
    assert dt is not None
    assert dt.year == 2026 and dt.month == 7


# ---------------------------------------------------------------------------
# _p3_history_features
# ---------------------------------------------------------------------------

def test_p3_history_features_no_logs_uses_current_as_baseline():
    velocity, proc_mean, torque_mean, rpm_mean = predictions._p3_history_features(
        [], machine_id=1, current_process=310.0, current_torque=40.0,
        current_rpm=1500.0, current_wear=5.0,
    )
    assert velocity == 0.0
    assert proc_mean == 310.0
    assert torque_mean == 40.0
    assert rpm_mean == 1500.0


def test_p3_history_features_with_history_filters_other_machines():
    logs = [
        {"machine_id": 2, "created_at": "2026-01-01", "tool_wear": 99.0},
        {"machine_id": 1, "created_at": "2026-01-02", "tool_wear": 10.0,
         "process_temperature": 305.0, "torque": 35.0, "rotational_speed": 1400.0},
    ]
    velocity, proc_mean, torque_mean, rpm_mean = predictions._p3_history_features(
        logs, machine_id=1, current_process=310.0, current_torque=40.0,
        current_rpm=1500.0, current_wear=15.0,
    )
    assert velocity == 5.0
    assert proc_mean == pytest.approx((305.0 + 310.0) / 2)
    assert torque_mean == pytest.approx((35.0 + 40.0) / 2)
    assert rpm_mean == pytest.approx((1400.0 + 1500.0) / 2)


# ---------------------------------------------------------------------------
# _filter_dst_inputs
# ---------------------------------------------------------------------------

def test_filter_dst_inputs_drops_none_and_placeholder():
    outputs = [
        None,
        {"model_id": "model_c_mahal_hi", "health_index": 80.0, "score_source": "no_model"},
        {"model_id": "model_b_survival", "health_index": 70.0},
        {"model_id": "model_e_anomaly", "health_index": float("nan")},
    ]
    result = predictions._filter_dst_inputs(outputs, maintenance_event=False)
    assert result == [{"model_id": "model_b_survival", "health_index": 70.0}]


def test_filter_dst_inputs_excludes_on_maintenance_event():
    outputs = [
        {"model_id": "model_c_mahal_hi", "health_index": 80.0},
        {"model_id": "model_e_anomaly", "health_index": 60.0},
        {"model_id": "model_b_survival", "health_index": 70.0},
    ]
    result = predictions._filter_dst_inputs(outputs, maintenance_event=True)
    assert result == [{"model_id": "model_b_survival", "health_index": 70.0}]


# ---------------------------------------------------------------------------
# _p4_norm
# ---------------------------------------------------------------------------

def test_p4_norm_within_range():
    thresholds = {"if_min": 0.0, "if_max": 10.0}
    assert predictions._p4_norm("if", 5.0, thresholds) == 0.5


def test_p4_norm_clips_above_max():
    thresholds = {"if_min": 0.0, "if_max": 10.0}
    assert predictions._p4_norm("if", 20.0, thresholds) == 1.0


def test_p4_norm_equal_bounds_returns_half():
    thresholds = {"if_min": 5.0, "if_max": 5.0}
    assert predictions._p4_norm("if", 5.0, thresholds) == 0.5


# ---------------------------------------------------------------------------
# _p4_if_fallback
# ---------------------------------------------------------------------------

class _FakeIFModel:
    def __init__(self, pred, score):
        self._pred = pred
        self._score = score

    def predict(self, x):
        return np.array([self._pred])

    def decision_function(self, x):
        return np.array([self._score])


def test_p4_if_fallback_anomaly_detected():
    model = _FakeIFModel(pred=-1, score=-0.2)
    is_anomaly, score = predictions._p4_if_fallback(model, [1, 2, 3, 4, 5])
    assert is_anomaly is True
    assert score == 0.2


def test_p4_if_fallback_normal():
    model = _FakeIFModel(pred=1, score=0.3)
    is_anomaly, score = predictions._p4_if_fallback(model, [1, 2, 3, 4, 5])
    assert is_anomaly is False
    assert score == -0.3


def test_p4_if_fallback_on_exception_returns_safe_default():
    class _Broken:
        def predict(self, x):
            raise RuntimeError("boom")

    is_anomaly, score = predictions._p4_if_fallback(_Broken(), [1, 2, 3, 4, 5])
    assert is_anomaly is False
    assert score == 0.0


# ---------------------------------------------------------------------------
# MachineLearningService.predict_failure_probability
# ---------------------------------------------------------------------------

def test_predict_failure_probability_no_model(monkeypatch):
    monkeypatch.setattr(predictions, "load_p1", lambda: None)
    assert MachineLearningService.predict_failure_probability([1] * 7) == 0.0


def test_predict_failure_probability_success(monkeypatch):
    class _FakeP1:
        def predict_proba(self, X):
            return np.array([[0.3, 0.7]])

    monkeypatch.setattr(predictions, "load_p1", lambda: _FakeP1())
    prob = MachineLearningService.predict_failure_probability([1] * 7)
    assert prob == 70.0


def test_predict_failure_probability_on_exception(monkeypatch):
    class _Broken:
        def predict_proba(self, X):
            raise RuntimeError("boom")

    monkeypatch.setattr(predictions, "load_p1", lambda: _Broken())
    assert MachineLearningService.predict_failure_probability([1] * 7) == 0.0


# ---------------------------------------------------------------------------
# MachineLearningService.predict_failure_type
# ---------------------------------------------------------------------------

def test_predict_failure_type_no_model(monkeypatch):
    monkeypatch.setattr(predictions, "load_p2", lambda: None)
    assert MachineLearningService.predict_failure_type([1] * 7) == {}


def test_predict_failure_type_success(monkeypatch):
    class _Estimator:
        def __init__(self, proba):
            self._proba = proba

        def predict_proba(self, X):
            return np.array([[1 - self._proba, self._proba]])

    class _FakeP2Model:
        estimators_ = [_Estimator(0.9), _Estimator(0.1)]

        def predict(self, X):
            return [[1, 0]]

    monkeypatch.setattr(
        predictions, "load_p2",
        lambda: {"model": _FakeP2Model(), "labels": ["TWF", "HDF"]},
    )
    result = MachineLearningService.predict_failure_type([1] * 7)
    assert result["TWF"]["detected"] is True
    assert result["TWF"]["probability"] == 90.0
    assert result["HDF"]["detected"] is False


def test_predict_failure_type_on_exception(monkeypatch):
    class _Broken:
        def predict(self, X):
            raise RuntimeError("boom")

    monkeypatch.setattr(predictions, "load_p2", lambda: {"model": _Broken(), "labels": []})
    assert MachineLearningService.predict_failure_type([1] * 7) == {}


# ---------------------------------------------------------------------------
# MachineLearningService.predict_rul
# ---------------------------------------------------------------------------

def test_predict_rul_no_model(monkeypatch):
    monkeypatch.setattr(predictions, "load_p3", lambda: None)
    assert MachineLearningService.predict_rul([1] * 11) is None


def test_predict_rul_success(monkeypatch):
    class _FakeP3:
        n_features_in_ = 7

        def predict(self, X):
            return np.array([12.5])

    monkeypatch.setattr(predictions, "load_p3", lambda: _FakeP3())
    assert MachineLearningService.predict_rul([1] * 11) == 12.5


def test_predict_rul_on_exception(monkeypatch):
    class _Broken:
        def predict(self, X):
            raise RuntimeError("boom")

    monkeypatch.setattr(predictions, "load_p3", lambda: _Broken())
    assert MachineLearningService.predict_rul([1] * 11) is None


# ---------------------------------------------------------------------------
# MachineLearningService.predict_rul_interval
# ---------------------------------------------------------------------------

def test_predict_rul_interval_no_quantile_model(monkeypatch):
    monkeypatch.setattr(predictions, "load_p3_quantile", lambda: None)
    assert MachineLearningService.predict_rul_interval([1] * 11) is None


def test_predict_rul_interval_missing_model_key(monkeypatch):
    monkeypatch.setattr(predictions, "load_p3_quantile", lambda: {"model": None})
    assert MachineLearningService.predict_rul_interval([1] * 11) is None


def test_predict_rul_interval_success(monkeypatch):
    class _FakeQuantile:
        n_features_in_ = 11

        def predict(self, X):
            return np.array([[8.0, 12.0, 18.0]])

    monkeypatch.setattr(
        predictions, "load_p3_quantile",
        lambda: {"model": _FakeQuantile(), "levels": [0.1, 0.5, 0.9]},
    )
    result = MachineLearningService.predict_rul_interval([1] * 11)
    assert result == {"p10": 8.0, "p50": 12.0, "p90": 18.0}


def test_predict_rul_interval_on_exception(monkeypatch):
    class _Broken:
        def predict(self, X):
            raise RuntimeError("boom")

    monkeypatch.setattr(predictions, "load_p3_quantile", lambda: {"model": _Broken()})
    assert MachineLearningService.predict_rul_interval([1] * 11) is None


# ---------------------------------------------------------------------------
# MachineLearningService.detect_anomaly
# ---------------------------------------------------------------------------

def test_detect_anomaly_no_model(monkeypatch):
    monkeypatch.setattr(predictions, "load_p4", lambda: None)
    assert MachineLearningService.detect_anomaly([1] * 5) == (False, 0.0)


def test_detect_anomaly_success(monkeypatch):
    class _FakeIF:
        def decision_function(self, x):
            return np.array([-0.6])

    p4 = {
        "model": _FakeIF(),
        "weights": {"if": 0.5, "zscore": 0.5},
        "thresholds": {"if_min": 0.0, "if_max": 1.0, "zscore_min": 0.0, "zscore_max": 5.0},
        "training_stats": {"mean": [300, 310, 1500, 40, 0], "std": [2, 1.5, 179, 10, 1]},
    }
    monkeypatch.setattr(predictions, "load_p4", lambda: p4)
    is_anomaly, score = MachineLearningService.detect_anomaly([320.0, 310.0, 1500.0, 40.0, 0.0])
    assert isinstance(is_anomaly, bool)
    assert 0.0 <= score <= 1.0


def test_detect_anomaly_on_exception_falls_back(monkeypatch):
    class _FakeIF:
        def decision_function(self, x):
            raise RuntimeError("boom")

        def predict(self, x):
            return np.array([1])

    p4 = {
        "model": _FakeIF(),
        "weights": {"if": 1.0},
        "thresholds": {},
        "training_stats": {},
    }
    monkeypatch.setattr(predictions, "load_p4", lambda: p4)
    is_anomaly, score = MachineLearningService.detect_anomaly([1] * 5)
    assert is_anomaly is False
    assert score == 0.0


# ---------------------------------------------------------------------------
# MachineLearningService.predict_priority
# ---------------------------------------------------------------------------

def test_predict_priority_no_model(monkeypatch):
    monkeypatch.setattr(predictions, "load_p5", lambda: None)
    assert MachineLearningService.predict_priority([1] * 7) == "Medium"


def test_predict_priority_success(monkeypatch):
    class _FakeP5:
        def predict(self, X):
            return [1]

    monkeypatch.setattr(
        predictions, "load_p5",
        lambda: {"model": _FakeP5(), "labels": ["Low", "High"]},
    )
    assert MachineLearningService.predict_priority([1] * 7) == "High"


def test_predict_priority_on_exception(monkeypatch):
    class _Broken:
        def predict(self, X):
            raise RuntimeError("boom")

    monkeypatch.setattr(predictions, "load_p5", lambda: {"model": _Broken(), "labels": []})
    assert MachineLearningService.predict_priority([1] * 7) == "Medium"


# ---------------------------------------------------------------------------
# MachineLearningService.predict_maintenance_schedule
# ---------------------------------------------------------------------------

def test_predict_maintenance_schedule_no_model(monkeypatch):
    monkeypatch.setattr(predictions, "load_p6", lambda: None)
    assert MachineLearningService.predict_maintenance_schedule([1] * 7) == 7.0


def test_predict_maintenance_schedule_success_default_squared_wear(monkeypatch):
    class _FakeP6:
        def predict(self, X):
            return [9.0]

    monkeypatch.setattr(predictions, "load_p6", lambda: _FakeP6())
    features = [300.0, 310.0, 1500.0, 40.0, 5.0, 10.0, 60.0]
    assert MachineLearningService.predict_maintenance_schedule(features) == 9.0


def test_predict_maintenance_schedule_on_exception(monkeypatch):
    class _Broken:
        def predict(self, X):
            raise RuntimeError("boom")

    monkeypatch.setattr(predictions, "load_p6", lambda: _Broken())
    assert MachineLearningService.predict_maintenance_schedule([1] * 7) == 7.0


# ---------------------------------------------------------------------------
# MachineLearningService.predict_parts_demand
# ---------------------------------------------------------------------------

def test_predict_parts_demand_no_model(monkeypatch):
    monkeypatch.setattr(predictions, "load_p7", lambda: None)
    result = MachineLearningService.predict_parts_demand(1, 30.0, {}, horizon_days=30)
    assert result["source"] == "deterministic_fallback"
    assert result["items"] == []


def test_predict_parts_demand_success_empty_maps(monkeypatch):
    monkeypatch.setattr(
        predictions, "load_p7",
        lambda: {
            "failure_part_map": {}, "consumable_params": {},
            "parts_catalog": {}, "meta": {"theta": 0.05},
        },
    )
    result = MachineLearningService.predict_parts_demand(1, 30.0, {"TWF": 0.5}, horizon_days=30)
    assert result["source"] == "p7_model"
    assert result["items"] == []


def test_predict_parts_demand_on_exception_falls_back(monkeypatch):
    monkeypatch.setattr(
        predictions, "load_p7",
        lambda: {"failure_part_map": {}, "consumable_params": {}, "parts_catalog": {}, "meta": {}},
    )

    def _boom(*a, **kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(predictions, "survival_demand", _boom)
    result = MachineLearningService.predict_parts_demand(1, 30.0, {"TWF": 0.5}, horizon_days=30)
    assert result["source"] == "deterministic_fallback"
    assert result["items"] == []


# ---------------------------------------------------------------------------
# _run_shap_explanations
# ---------------------------------------------------------------------------

def test_run_shap_explanations_disabled_returns_empty():
    assert predictions._run_shap_explanations(False, [1] * 7) == []


def test_run_shap_explanations_no_model_returns_empty(monkeypatch):
    monkeypatch.setattr(predictions, "load_p1", lambda: None)
    assert predictions._run_shap_explanations(True, [1] * 7) == []


# ---------------------------------------------------------------------------
# MachineLearningService.predict_all — thin integration smoke test
# ---------------------------------------------------------------------------

def test_predict_all_with_no_models_returns_defaults(monkeypatch):
    monkeypatch.setattr(predictions, "load_p1", lambda: None)
    monkeypatch.setattr(predictions, "load_p2", lambda: None)
    monkeypatch.setattr(predictions, "load_p3", lambda: None)
    monkeypatch.setattr(predictions, "load_p3_quantile", lambda: None)
    monkeypatch.setattr(predictions, "load_p4", lambda: None)
    monkeypatch.setattr(predictions, "load_p5", lambda: None)
    monkeypatch.setattr(predictions, "load_p6", lambda: None)
    monkeypatch.setattr(predictions, "load_p7", lambda: None)

    telemetry = {
        "air_temperature": 300.0, "process_temperature": 310.0,
        "rotational_speed": 1500, "torque": 40.0, "tool_wear": 5.0,
        "machine_id": 1,
    }
    result = MachineLearningService.predict_all(telemetry)

    assert result["p1_failure_probability"] == 0.0
    assert result["p1_risk_level"] == "LOW"
    assert result["p2_failure_types"] == {}
    assert result["p3_rul_days"] is None
    assert result["p4_is_anomaly"] is False
    assert result["p5_predicted_priority"] == "Medium"
    assert result["p6_schedule_days"] == 7.0
    assert result["p7_parts_demand"]["source"] == "deterministic_fallback"
    assert "unified_health_score" in result
    assert result["shap_explanations"] == []
