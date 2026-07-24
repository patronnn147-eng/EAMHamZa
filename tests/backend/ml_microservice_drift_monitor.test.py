"""Unit coverage for app/ml-microservice/src/drift_monitor.py — pure
numpy/pandas/scipy, no DB or model artifacts needed. Imported via
`src.drift_monitor` for the same reason as ml_microservice_predictions.test.py
(package-relative usage inside the module itself, if any is added later)."""
import sys
import os
import importlib

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../app/ml-microservice'))

drift_monitor = importlib.import_module("src.drift_monitor")
DriftMonitor = drift_monitor.DriftMonitor


def _df(**cols):
    return pd.DataFrame(cols)


# ── __init__ ─────────────────────────────────────────────────────────────────

def test_init_auto_selects_numeric_columns():
    ref = _df(a=[1.0, 2.0, 3.0], b=[4, 5, 6], label=["x", "y", "z"])
    monitor = DriftMonitor(reference_data=ref)
    assert set(monitor.feature_cols) == {"a", "b"}


def test_init_respects_explicit_feature_cols():
    ref = _df(a=[1.0, 2.0], b=[4, 5])
    monitor = DriftMonitor(reference_data=ref, feature_cols=["a"])
    assert monitor.feature_cols == ["a"]


def test_set_reference_anomaly_rate():
    monitor = DriftMonitor(reference_data=_df(a=[1.0]))
    monitor.set_reference_anomaly_rate(0.034)
    assert monitor.reference_anomaly_rate == 0.034


# ── _ks_severity ─────────────────────────────────────────────────────────────

def test_ks_severity_critical():
    monitor = DriftMonitor(reference_data=_df(a=[1.0]))
    assert monitor._ks_severity(0.005) == "critical"


def test_ks_severity_warning():
    monitor = DriftMonitor(reference_data=_df(a=[1.0]))
    assert monitor._ks_severity(0.03) == "warning"


def test_ks_severity_none():
    monitor = DriftMonitor(reference_data=_df(a=[1.0]))
    assert monitor._ks_severity(0.5) == "none"


# ── _check_feature ────────────────────────────────────────────────────────────

def test_check_feature_missing_column_returns_none():
    ref = _df(a=list(range(40)))
    monitor = DriftMonitor(reference_data=ref, feature_cols=["a"])
    current = _df(b=list(range(40)))
    assert monitor._check_feature("a", current) is None


def test_check_feature_too_few_samples_returns_none():
    ref = _df(a=list(range(40)))
    monitor = DriftMonitor(reference_data=ref, feature_cols=["a"])
    current = _df(a=list(range(10)))  # < 30 samples
    assert monitor._check_feature("a", current) is None


def test_check_feature_no_drift_when_identical_distribution():
    ref = _df(a=list(range(40)))
    monitor = DriftMonitor(reference_data=ref, feature_cols=["a"])
    current = _df(a=list(range(40)))
    result = monitor._check_feature("a", current)
    assert result is not None
    assert result.drift_detected is False
    assert result.severity == "none"


def test_check_feature_detects_critical_drift_on_shifted_distribution():
    ref = _df(a=list(range(40)))
    monitor = DriftMonitor(reference_data=ref, feature_cols=["a"])
    current = _df(a=list(range(1000, 1040)))  # completely disjoint range
    result = monitor._check_feature("a", current)
    assert result.drift_detected is True
    assert result.severity == "critical"
    assert result.mean_shift_pct > 0


# ── _check_prediction_drift ───────────────────────────────────────────────────

def test_check_prediction_drift_none_when_no_predictions():
    monitor = DriftMonitor(reference_data=_df(a=[1.0]))
    assert monitor._check_prediction_drift(None) is None


def test_check_prediction_drift_none_when_no_reference_stored():
    monitor = DriftMonitor(reference_data=_df(a=[1.0]))
    assert monitor._check_prediction_drift(np.array([1.0, 2.0])) is None


def test_check_prediction_drift_detects_shift():
    monitor = DriftMonitor(reference_data=_df(a=[1.0]))
    monitor.set_reference_predictions(np.arange(0, 40, dtype=float))
    result = monitor._check_prediction_drift(np.arange(1000, 1040, dtype=float))
    assert result.feature == "predictions"
    assert result.drift_detected is True


def test_check_prediction_drift_no_drift_for_identical_dist():
    monitor = DriftMonitor(reference_data=_df(a=[1.0]))
    ref_preds = np.arange(0, 40, dtype=float)
    monitor.set_reference_predictions(ref_preds)
    result = monitor._check_prediction_drift(ref_preds.copy())
    assert result.drift_detected is False


# ── _check_anomaly_rate ──────────────────────────────────────────────────────

def test_check_anomaly_rate_no_flags_returns_false_none():
    monitor = DriftMonitor(reference_data=_df(a=[1.0]))
    monitor.set_reference_anomaly_rate(0.05)
    alert, rate = monitor._check_anomaly_rate(None)
    assert alert is False
    assert rate is None


def test_check_anomaly_rate_no_reference_returns_false_none():
    monitor = DriftMonitor(reference_data=_df(a=[1.0]))
    alert, rate = monitor._check_anomaly_rate(np.array([1, 1, 0]))
    assert alert is False
    assert rate is None


def test_check_anomaly_rate_spike_detected():
    monitor = DriftMonitor(reference_data=_df(a=[1.0]))
    monitor.set_reference_anomaly_rate(0.05)
    flags = np.array([1, 1, 1, 0, 0])  # rate = 0.6, way above 0.05*2
    alert, rate = monitor._check_anomaly_rate(flags)
    assert alert is True
    assert rate == pytest.approx(0.6)


def test_check_anomaly_rate_no_spike():
    monitor = DriftMonitor(reference_data=_df(a=[1.0]))
    monitor.set_reference_anomaly_rate(0.5)
    flags = np.array([1, 0, 0, 0, 0])  # rate = 0.2, below 0.5*2
    alert, rate = monitor._check_anomaly_rate(flags)
    assert alert is False
    assert rate == pytest.approx(0.2)


# ── _build_drift_summary ─────────────────────────────────────────────────────

def test_build_drift_summary_no_drift():
    summary = DriftMonitor._build_drift_summary([], None, None, False, None)
    assert summary == "No drift detected."


def test_build_drift_summary_critical_and_warning():
    FeatureDriftResult = drift_monitor.FeatureDriftResult
    critical = FeatureDriftResult("torque", 0.5, 0.001, True, "critical", 40.0, 55.0, 37.5)
    warning = FeatureDriftResult("rpm", 0.3, 0.03, True, "warning", 1500.0, 1550.0, 3.3)
    summary = DriftMonitor._build_drift_summary([critical, warning], None, None, False, None)
    assert "CRITICAL drift: torque" in summary
    assert "WARNING drift: rpm" in summary


def test_build_drift_summary_anomaly_spike():
    summary = DriftMonitor._build_drift_summary([], None, 0.6, True, 0.05)
    assert "Anomaly rate spike: 0.600 (ref=0.050)" in summary


# ── check() — full integration ──────────────────────────────────────────────

def test_check_no_drift_report():
    ref = _df(a=list(range(40)), b=list(range(40)))
    monitor = DriftMonitor(reference_data=ref)
    current = _df(a=list(range(40)), b=list(range(40)))
    report = monitor.check(current_data=current)
    assert report.any_drift is False
    assert report.n_features_drifted == 0
    assert report.summary == "No drift detected."
    assert report.timestamp  # ISO string present


def test_check_detects_feature_drift():
    ref = _df(a=list(range(40)), b=list(range(40)))
    monitor = DriftMonitor(reference_data=ref)
    current = _df(a=list(range(1000, 1040)), b=list(range(40)))
    report = monitor.check(current_data=current)
    assert report.any_drift is True
    assert report.n_features_drifted == 1


def test_check_includes_anomaly_rate_alert_in_any_drift():
    ref = _df(a=list(range(40)))
    monitor = DriftMonitor(reference_data=ref)
    monitor.set_reference_anomaly_rate(0.05)
    current = _df(a=list(range(40)))
    flags = np.array([1] * 20 + [0] * 20)  # rate 0.5, well above spike threshold
    report = monitor.check(current_data=current, current_anomaly_flags=flags)
    assert report.any_drift is True
    assert report.anomaly_rate_alert is True


def test_check_report_to_dict_is_json_serializable():
    ref = _df(a=list(range(40)))
    monitor = DriftMonitor(reference_data=ref)
    report = monitor.check(current_data=_df(a=list(range(40))))
    d = report.to_dict()
    import json
    json.dumps(d)  # must not raise


# ── from_training_data ───────────────────────────────────────────────────────

def test_from_training_data_sets_reference_anomaly_rate():
    X_train = _df(a=list(range(40)))
    y_train = np.array([0] * 38 + [1] * 2)
    monitor = DriftMonitor.from_training_data(X_train, y_train=y_train)
    assert monitor.reference_anomaly_rate == pytest.approx(0.05)


def test_from_training_data_sets_reference_predictions():
    X_train = _df(a=list(range(40)))
    preds = np.arange(0, 40, dtype=float)
    monitor = DriftMonitor.from_training_data(X_train, predictions_train=preds)
    assert hasattr(monitor, "_reference_predictions")


def test_from_training_data_without_optional_args():
    X_train = _df(a=list(range(40)))
    monitor = DriftMonitor.from_training_data(X_train)
    assert monitor.reference_anomaly_rate is None
    assert not hasattr(monitor, "_reference_predictions")
