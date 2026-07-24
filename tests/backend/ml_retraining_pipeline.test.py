"""Unit tests for the deep model-fitting/orchestration logic in
app/backend/modules/ml/services/ml_retraining.py — get_retraining_stats,
_prepare_model_targets, _fit_model_for_type, _eval_accuracy_gate,
_repeated_holdout_scores, _retrain_one_model, _retrain_all_models, and
run_retraining_pipeline. See ml_retraining_helpers.test.py for the
already-covered pure helpers (validate_model, _backup_model, _align_training_features, etc)."""
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import numpy as np
import pandas as pd
import pytest

from modules.ml.services import ml_retraining as mr
from modules.ml.services.ml_retraining import RetrainingService


def _toy_df(n=24, machine_ids=None, seed=0):
    rng = np.random.RandomState(seed)
    machine_ids = machine_ids or [None] * n
    failure = [1 if i % 6 == 0 else 0 for i in range(n)]
    ft_labels = ["TWF" if i % 6 == 0 else "NONE" for i in range(n)]
    priorities = ["URGENTE", "ÉLEVÉE", "MOYENNE", "BASSE"] * (n // 4 + 1)
    air = rng.normal(300, 2, n)
    process = rng.normal(310, 1.5, n)
    rpm = rng.normal(1500, 100, n)
    torque = rng.normal(40, 8, n)
    wear = rng.uniform(0, 200, n)
    return pd.DataFrame({
        mr._COL_AIR_TEMP: air,
        mr._COL_PROCESS_TEMP: process,
        mr._COL_RPM: rpm,
        mr._COL_TORQUE: torque,
        mr._COL_TOOL_WEAR: wear,
        mr._COL_MACHINE_FAILURE: failure,
        "actual_failure_type": ft_labels,
        "priority": priorities[:n],
        "machine_id": machine_ids,
        # Engineered columns _align_training_features forces for mt == "p3" —
        # required whenever a test exercises _retrain_one_model/_align_training_features
        # with mt="p3" directly (bypassing the real _engineer_training_features call).
        "temp_delta": process - air,
        "rpm_torque": rpm * torque / 1000.0,
        "tool_wear_velocity": 0.0,
        "process_temp_roll5_mean": process,
        "torque_roll5_mean": torque,
        "rpm_roll5_mean": rpm,
    })


def _safe_X(df):
    """Strip XGBoost-illegal characters from feature names, matching what
    _align_training_features does before any model ever sees these columns —
    real column names like "Air temperature [K]" contain '[' ']' which
    XGBoost's DMatrix rejects outright."""
    X = df[mr._BASE_COLUMNS].copy()
    X.columns = [c.replace("[", "").replace("]", "").replace("<", "").strip() for c in X.columns]
    return X


class FakeScalarOneDb:
    def __init__(self, value):
        self._value = value

    async def execute(self, *_a, **_k):
        return SimpleNamespace(scalar_one=lambda: self._value)


# ── get_retraining_stats ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_retraining_stats_returns_count():
    result = await RetrainingService.get_retraining_stats(FakeScalarOneDb(7))
    assert result == {"new_data_points": 7}


# ── _prepare_model_targets ───────────────────────────────────────────────────

def test_prepare_model_targets_p6_returns_none():
    df = _toy_df(10)
    assert RetrainingService._prepare_model_targets("p6", df, df) is None


def test_prepare_model_targets_p2_builds_multilabel_targets():
    df = _toy_df(12)
    result = RetrainingService._prepare_model_targets("p2", df, df)
    assert list(result["y"].columns) == mr._FAILURE_TYPES
    assert result["labels"] == mr._FAILURE_TYPES
    assert result["y"]["TWF"].sum() > 0


def test_prepare_model_targets_p3_builds_rul_proxy():
    df = _toy_df(12)
    result = RetrainingService._prepare_model_targets("p3", df, df)
    assert "y" in result
    assert (result["y"] >= 0).all()


def test_prepare_model_targets_p5_maps_priority():
    df = _toy_df(12)
    result = RetrainingService._prepare_model_targets("p5", df, df)
    assert set(result["y"].unique()).issubset({0, 1, 2, 3})


def test_prepare_model_targets_p5_missing_priority_defaults_moyenne():
    df = _toy_df(4).drop(columns=["priority"])
    result = RetrainingService._prepare_model_targets("p5", df, df)
    assert (result["y"] == 2).all()  # MOYENNE


def test_prepare_model_targets_default_uses_machine_failure():
    df = _toy_df(10)
    result = RetrainingService._prepare_model_targets("p1", df, df)
    assert list(result["y"]) == list(df[mr._COL_MACHINE_FAILURE])


# ── _fit_model_for_type ──────────────────────────────────────────────────────

def test_fit_model_for_type_unknown_returns_none():
    df = _toy_df(10)
    X = _safe_X(df)
    targets = RetrainingService._prepare_model_targets("p1", df, df)
    assert RetrainingService._fit_model_for_type("p9", X, targets, {}, 10) is None


def test_fit_model_for_type_p1_fits_classifier():
    df = _toy_df(24)
    X = _safe_X(df)
    targets = RetrainingService._prepare_model_targets("p1", df, df)
    result = RetrainingService._fit_model_for_type("p1", X, targets, {"features": mr._BASE_COLUMNS}, 24)
    assert result["model"] is not None
    assert result["features"] == mr._BASE_COLUMNS
    preds = result["model"].predict(X)
    assert len(preds) == 24


def test_fit_model_for_type_p2_fits_multioutput_with_per_label_weighting():
    df = _toy_df(24)
    X = _safe_X(df)
    targets = RetrainingService._prepare_model_targets("p2", df, df)
    result = RetrainingService._fit_model_for_type("p2", X, targets, {"features": mr._BASE_COLUMNS}, 24)
    assert result["labels"] == mr._FAILURE_TYPES
    preds = result["model"].predict(X)
    assert preds.shape == (24, 5)


def test_fit_model_for_type_p3_fits_regressor_with_quantile_head():
    df = _toy_df(24)
    X = _safe_X(df)
    targets = RetrainingService._prepare_model_targets("p3", df, df)
    result = RetrainingService._fit_model_for_type("p3", X, targets, {"features": mr._BASE_COLUMNS}, 24)
    assert result["model"] is not None
    assert result["metrics"]["rul_source"] == "tool_wear_proxy"
    # quantile head is best-effort; if it succeeded, levels line up
    if "quantile_model" in result:
        assert result["quantile_levels"] == [0.1, 0.5, 0.9]


def test_fit_model_for_type_p4_fits_isolation_forest():
    df = _toy_df(24)
    X = _safe_X(df)
    targets = RetrainingService._prepare_model_targets("p4", df, df)
    result = RetrainingService._fit_model_for_type("p4", X, targets, {"features": mr._BASE_COLUMNS}, 24)
    assert result["weights"] == {"if": 0.30, "zscore": 0.20}
    assert "if_min" in result["thresholds"]
    assert len(result["training_stats"]["mean"]) == 5


def test_fit_model_for_type_p5_fits_priority_classifier():
    df = _toy_df(24)
    X = _safe_X(df)
    targets = RetrainingService._prepare_model_targets("p5", df, df)
    result = RetrainingService._fit_model_for_type("p5", X, targets, {"features": mr._BASE_COLUMNS}, 24)
    assert result["labels"] == ["URGENTE", "ÉLEVÉE", "MOYENNE", "BASSE"]
    preds = result["model"].predict(X)
    assert len(preds) == 24


# ── _eval_accuracy_gate ───────────────────────────────────────────────────────

def test_eval_accuracy_gate_p1_computes_f1_and_auc():
    df = _toy_df(24)
    X = _safe_X(df)
    targets = RetrainingService._prepare_model_targets("p1", df, df)
    model_data = RetrainingService._fit_model_for_type("p1", X, targets, {}, 24)
    passed, metrics = RetrainingService._eval_accuracy_gate("p1", model_data, X, targets, min_f1=0.0, min_r2=0.0)
    assert passed is True  # min_f1=0.0 always passes
    assert "val_f1" in metrics


def test_eval_accuracy_gate_p2_macro_f1():
    df = _toy_df(24)
    X = _safe_X(df)
    targets = RetrainingService._prepare_model_targets("p2", df, df)
    model_data = RetrainingService._fit_model_for_type("p2", X, targets, {}, 24)
    passed, metrics = RetrainingService._eval_accuracy_gate("p2", model_data, X, targets, min_f1=0.0, min_r2=0.0)
    assert "val_f1_macro" in metrics


def test_eval_accuracy_gate_p3_r2():
    df = _toy_df(24)
    X = _safe_X(df)
    targets = RetrainingService._prepare_model_targets("p3", df, df)
    model_data = RetrainingService._fit_model_for_type("p3", X, targets, {}, 24)
    passed, metrics = RetrainingService._eval_accuracy_gate("p3", model_data, X, targets, min_f1=0.0, min_r2=-999.0)
    assert passed is True
    assert "val_r2" in metrics


def test_eval_accuracy_gate_p5_macro_f1():
    df = _toy_df(24)
    X = _safe_X(df)
    targets = RetrainingService._prepare_model_targets("p5", df, df)
    model_data = RetrainingService._fit_model_for_type("p5", X, targets, {}, 24)
    passed, metrics = RetrainingService._eval_accuracy_gate("p5", model_data, X, targets, min_f1=0.0, min_r2=0.0)
    assert "val_f1_macro" in metrics


def test_eval_accuracy_gate_unsupervised_p4_always_passes():
    df = _toy_df(24)
    X = _safe_X(df)
    targets = RetrainingService._prepare_model_targets("p4", df, df)
    model_data = RetrainingService._fit_model_for_type("p4", X, targets, {}, 24)
    passed, metrics = RetrainingService._eval_accuracy_gate("p4", model_data, X, targets, min_f1=0.99, min_r2=0.99)
    assert passed is True
    assert metrics == {}


def test_eval_accuracy_gate_swallows_prediction_failure():
    class _Broken:
        def predict(self, X):
            raise RuntimeError("boom")

    model_data = {"model": _Broken()}
    passed, metrics = RetrainingService._eval_accuracy_gate(
        "p1", model_data, pd.DataFrame({"a": [1]}), {"y_val": [0]}, min_f1=0.9, min_r2=0.9,
    )
    assert passed is True  # infra failure doesn't block
    assert metrics == {}


def test_eval_accuracy_gate_below_threshold_fails():
    df = _toy_df(24)
    X = _safe_X(df)
    targets = RetrainingService._prepare_model_targets("p3", df, df)
    model_data = RetrainingService._fit_model_for_type("p3", X, targets, {}, 24)
    passed, _ = RetrainingService._eval_accuracy_gate("p3", model_data, X, targets, min_f1=0.0, min_r2=999.0)
    assert passed is False


# ── _repeated_holdout_scores ─────────────────────────────────────────────────

def test_repeated_holdout_scores_returns_per_fold_f1():
    machine_ids_col = [1] * 12 + [2] * 12
    df = _toy_df(24, machine_ids=machine_ids_col)
    scores = RetrainingService._repeated_holdout_scores(
        "p5", df, machine_ids=[1, 2], existing_features=mr._BASE_COLUMNS,
        xgb_features=mr._BASE_COLUMNS, existing_data={},
    )
    assert isinstance(scores, list)
    assert len(scores) <= 2
    assert all(0.0 <= s <= 1.0 for s in scores)


def test_repeated_holdout_scores_skips_empty_folds():
    df = _toy_df(10, machine_ids=[1] * 10)  # only one machine present
    scores = RetrainingService._repeated_holdout_scores(
        "p5", df, machine_ids=[1, 999], existing_features=mr._BASE_COLUMNS,
        xgb_features=mr._BASE_COLUMNS, existing_data={},
    )
    assert scores == []  # holdout=999 has no rows -> empty val fold, skipped


# ── _apply_repeated_holdout_metrics — success + exception-swallowed ───────────

def test_apply_repeated_holdout_metrics_success(monkeypatch):
    monkeypatch.setattr(
        RetrainingService, "_repeated_holdout_scores",
        staticmethod(lambda *a, **k: [0.7, 0.8, 0.75]),
    )
    gate_metrics = {}
    RetrainingService._apply_repeated_holdout_metrics(
        "p5", gate_metrics, full_df=_toy_df(10), machine_ids=[1, 2],
        existing_features=[], xgb_features=[], existing_data={},
    )
    assert gate_metrics["n_folds"] == 3
    assert "val_f1_macro_mean" in gate_metrics
    assert "val_f1_macro_std" in gate_metrics


def test_apply_repeated_holdout_metrics_swallows_failure(monkeypatch):
    def _raise(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(RetrainingService, "_repeated_holdout_scores", staticmethod(_raise))
    gate_metrics = {}
    RetrainingService._apply_repeated_holdout_metrics(
        "p5", gate_metrics, full_df=_toy_df(10), machine_ids=[1, 2],
        existing_features=[], xgb_features=[], existing_data={},
    )
    assert gate_metrics == {}  # untouched, no raise


# ── _retrain_one_model (orchestration) ───────────────────────────────────────

@pytest.fixture
def _stub_joblib(monkeypatch):
    monkeypatch.setattr(mr.joblib, "load", lambda path: {"features": mr._BASE_COLUMNS})
    dumped = {}
    monkeypatch.setattr(mr.joblib, "dump", lambda data, path: dumped.update({"data": data, "path": path}))
    monkeypatch.setattr(RetrainingService, "_cleanup_old_versions", staticmethod(lambda mt: None))
    return dumped


def test_retrain_one_model_skips_p6(_stub_joblib):
    df = _toy_df(10)
    result = RetrainingService._retrain_one_model("p6", "fake/path.pkl", df, df, 10, 0.7, 0.6)
    assert result == {"model": "p6", "status": "skipped", "reason": "P6 requires actual maintenance scheduling outcomes"}


def test_retrain_one_model_unknown_type_restores_backup(monkeypatch, _stub_joblib):
    monkeypatch.setattr(RetrainingService, "_backup_model", staticmethod(lambda mt: "backup.bak"))
    restored = {}
    monkeypatch.setattr(RetrainingService, "_restore_backup", staticmethod(lambda bp, mp: restored.update({"bp": bp, "mp": mp})))
    df = _toy_df(10)
    result = RetrainingService._retrain_one_model("p9", "fake/path.pkl", df, df, 10, 0.7, 0.6)
    assert result == {"model": "p9", "status": "skipped", "reason": "unknown model type"}
    assert restored["bp"] == "backup.bak"


def test_retrain_one_model_fit_exception_restores_backup(monkeypatch, _stub_joblib):
    monkeypatch.setattr(RetrainingService, "_backup_model", staticmethod(lambda mt: "backup.bak"))
    restored = {}
    monkeypatch.setattr(RetrainingService, "_restore_backup", staticmethod(lambda bp, mp: restored.update({"bp": bp})))

    def _raise(*a, **k):
        raise RuntimeError("fit exploded")

    monkeypatch.setattr(RetrainingService, "_fit_model_for_type", staticmethod(_raise))
    df = _toy_df(10)
    result = RetrainingService._retrain_one_model("p1", "fake/path.pkl", df, df, 10, 0.7, 0.6)
    assert result["status"] == "failed"
    assert "fit exploded" in result["error"]
    assert restored["bp"] == "backup.bak"


def test_retrain_one_model_invalid_model_restores_backup(monkeypatch, _stub_joblib):
    monkeypatch.setattr(RetrainingService, "_backup_model", staticmethod(lambda mt: None))
    monkeypatch.setattr(RetrainingService, "_fit_model_for_type", staticmethod(lambda *a, **k: {"model": None, "features": []}))
    df = _toy_df(10)
    result = RetrainingService._retrain_one_model("p1", "fake/path.pkl", df, df, 10, 0.7, 0.6)
    assert result["status"] == "failed"
    assert result["error"] == "No model object found"


def test_retrain_one_model_gate_rejected(monkeypatch, _stub_joblib):
    monkeypatch.setattr(RetrainingService, "_backup_model", staticmethod(lambda mt: None))
    monkeypatch.setattr(
        RetrainingService, "_fit_model_for_type",
        staticmethod(lambda *a, **k: {"model": object(), "features": ["a"]}),
    )
    monkeypatch.setattr(
        RetrainingService, "_eval_accuracy_gate",
        staticmethod(lambda *a, **k: (False, {"val_f1": 0.1})),
    )
    df = _toy_df(10)
    result = RetrainingService._retrain_one_model("p1", "fake/path.pkl", df, df, 10, 0.7, 0.6)
    assert result["status"] == "rejected"
    assert result["metrics"] == {"val_f1": 0.1}


def test_retrain_one_model_success_saves_model(monkeypatch, _stub_joblib):
    monkeypatch.setattr(RetrainingService, "_backup_model", staticmethod(lambda mt: "backup.bak"))
    monkeypatch.setattr(
        RetrainingService, "_fit_model_for_type",
        staticmethod(lambda *a, **k: {"model": object(), "features": ["a"]}),
    )
    monkeypatch.setattr(
        RetrainingService, "_eval_accuracy_gate",
        staticmethod(lambda *a, **k: (True, {"val_f1": 0.9})),
    )
    df = _toy_df(10)
    result = RetrainingService._retrain_one_model("p1", "fake/path.pkl", df, df, 10, 0.7, 0.6)
    assert result["status"] == "success"
    assert result["backup"] == "backup.bak"
    assert _stub_joblib["data"]["metrics"]["val_f1"] == 0.9


def test_retrain_one_model_p3_group_holdout_validated_status(monkeypatch, _stub_joblib):
    monkeypatch.setattr(RetrainingService, "_backup_model", staticmethod(lambda mt: None))
    monkeypatch.setattr(
        RetrainingService, "_fit_model_for_type",
        staticmethod(lambda *a, **k: {"model": object(), "features": ["a"]}),
    )
    monkeypatch.setattr(
        RetrainingService, "_eval_accuracy_gate",
        staticmethod(lambda *a, **k: (True, {"val_r2": 0.7})),
    )
    df = _toy_df(10)
    result = RetrainingService._retrain_one_model(
        "p3", "fake/path.pkl", df, df, 10, 0.7, 0.6, full_df=df, machine_ids=[1, 2],
    )
    assert result["val_metrics"]["validation_status"] == "group-holdout-validated"


def test_retrain_one_model_p3_unverified_with_too_few_machines(monkeypatch, _stub_joblib):
    monkeypatch.setattr(RetrainingService, "_backup_model", staticmethod(lambda mt: None))
    monkeypatch.setattr(
        RetrainingService, "_fit_model_for_type",
        staticmethod(lambda *a, **k: {"model": object(), "features": ["a"]}),
    )
    monkeypatch.setattr(
        RetrainingService, "_eval_accuracy_gate",
        staticmethod(lambda *a, **k: (True, {"val_r2": 0.7})),
    )
    df = _toy_df(10)
    result = RetrainingService._retrain_one_model(
        "p3", "fake/path.pkl", df, df, 10, 0.7, 0.6, full_df=df, machine_ids=None,
    )
    assert result["val_metrics"]["validation_status"] == "unverified"


# ── _retrain_all_models ──────────────────────────────────────────────────────

def test_retrain_all_models_skips_missing_files(tmp_path, monkeypatch):
    monkeypatch.setattr(mr, "MODELS_DIR", str(tmp_path))  # empty dir, no model files exist
    df = _toy_df(10)
    results = RetrainingService._retrain_all_models("all", df, df, 10, 0.7, 0.6, df, [])
    assert len(results) == len(mr.MODEL_FILES)
    assert all(r["status"] == "skipped" and r["reason"] == "Model file not found" for r in results)


def test_retrain_all_models_single_type_only():
    df = _toy_df(10)
    results = RetrainingService._retrain_all_models("p1", df, df, 10, 0.7, 0.6, df, [])
    assert len(results) == 1
    assert results[0]["model"] == "p1"


def test_retrain_all_models_unknown_type_produces_no_results():
    df = _toy_df(10)
    results = RetrainingService._retrain_all_models("p999", df, df, 10, 0.7, 0.6, df, [])
    assert results == []


def test_retrain_all_models_catches_per_model_exception(tmp_path, monkeypatch):
    (tmp_path / mr.MODEL_FILES["p1"]).write_text("dummy")
    monkeypatch.setattr(mr, "MODELS_DIR", str(tmp_path))

    def _raise(*a, **k):
        raise RuntimeError("catastrophic failure")

    monkeypatch.setattr(RetrainingService, "_retrain_one_model", staticmethod(_raise))
    df = _toy_df(10)
    results = RetrainingService._retrain_all_models("p1", df, df, 10, 0.7, 0.6, df, [])
    assert results[0]["status"] == "failed"
    assert "catastrophic failure" in results[0]["error"]


# ── run_retraining_pipeline ──────────────────────────────────────────────────

class FakeRunDb:
    def __init__(self, rows):
        self._rows = rows
        self.committed = 0
        self.rolled_back = 0

    async def execute(self, *_a, **_k):
        return SimpleNamespace(all=lambda: self._rows)

    async def commit(self):
        self.committed += 1

    async def rollback(self):
        self.rolled_back += 1


@pytest.mark.asyncio
async def test_run_retraining_pipeline_no_rows_skips():
    db = FakeRunDb([])
    result = await RetrainingService.run_retraining_pipeline(db)
    assert result["status"] == "skipped"
    assert result["models_retrained"] == []


@pytest.mark.asyncio
async def test_run_retraining_pipeline_success(monkeypatch):
    intervention = SimpleNamespace(id=1, actual_failure_type="TWF", machine_id=1, priority="HAUTE")
    log = SimpleNamespace(
        air_temperature=300.0, process_temperature=310.0, rotational_speed=1500,
        torque=40.0, tool_wear=10.0, created_at="2026-01-01",
    )
    db = FakeRunDb([(intervention, log)])

    combined_df = _toy_df(10)
    monkeypatch.setattr(RetrainingService, "_engineer_training_features", staticmethod(lambda new_data: combined_df))
    monkeypatch.setattr(
        RetrainingService, "_group_holdout_split",
        staticmethod(lambda df: (df.iloc[:8], df.iloc[8:], [1, 2])),
    )
    monkeypatch.setattr(
        RetrainingService, "_retrain_all_models",
        staticmethod(lambda *a, **k: [{"model": "p1", "status": "success"}]),
    )

    result = await RetrainingService.run_retraining_pipeline(db)

    assert result["status"] == "success"
    assert result["new_total_samples"] == len(combined_df)
    assert db.committed == 1


@pytest.mark.asyncio
async def test_run_retraining_pipeline_error_rolls_back(monkeypatch):
    intervention = SimpleNamespace(id=1, actual_failure_type="TWF", machine_id=1, priority="HAUTE")
    log = SimpleNamespace(
        air_temperature=300.0, process_temperature=310.0, rotational_speed=1500,
        torque=40.0, tool_wear=10.0, created_at="2026-01-01",
    )
    db = FakeRunDb([(intervention, log)])

    def _raise(new_data):
        raise RuntimeError("feature engineering exploded")

    monkeypatch.setattr(RetrainingService, "_engineer_training_features", staticmethod(_raise))

    result = await RetrainingService.run_retraining_pipeline(db)

    assert result["status"] == "error"
    assert "feature engineering exploded" in result["message"]
    assert db.rolled_back == 1
