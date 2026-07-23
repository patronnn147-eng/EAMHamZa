"""Unit tests for the RetrainingService helper methods extracted during the
2026-07 SonarQube cognitive-complexity refactor of ml_retraining.py."""
import os
from types import SimpleNamespace

import pandas as pd
import pytest

from modules.ml.services import ml_retraining as mr
from modules.ml.services.ml_retraining import RetrainingService


# ── validate_model ───────────────────────────────────────────────────────────

def test_validate_model_no_model_object():
    result = RetrainingService.validate_model("p1", {"features": ["a"]})
    assert result == {"valid": False, "error": "No model object found"}


def test_validate_model_no_features():
    result = RetrainingService.validate_model("p1", {"model": object(), "features": []})
    assert result == {"valid": False, "error": "No features defined"}


def test_validate_model_valid():
    result = RetrainingService.validate_model(
        "p1", {"model": object(), "features": ["a", "b"], "metrics": {"f1": 0.9}}
    )
    assert result["valid"] is True
    assert result["feature_count"] == 2
    assert result["metrics"] == {"f1": 0.9}


# ── _backup_model / _cleanup_old_versions ───────────────────────────────────

def test_backup_model_unknown_name_returns_none():
    assert RetrainingService._backup_model("not_a_model") is None


def test_backup_model_missing_file_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(mr, "MODELS_DIR", str(tmp_path))
    assert RetrainingService._backup_model("p1") is None


def test_backup_model_renames_existing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(mr, "MODELS_DIR", str(tmp_path))
    model_path = tmp_path / mr.MODEL_FILES["p1"]
    model_path.write_text("fake-pkl-content")

    backup_path = RetrainingService._backup_model("p1")

    assert backup_path is not None
    assert not model_path.exists()
    assert os.path.exists(backup_path)


def test_cleanup_old_versions_keeps_max_versions(tmp_path, monkeypatch):
    monkeypatch.setattr(mr, "MODELS_DIR", str(tmp_path))
    model_file = mr.MODEL_FILES["p1"]
    for i in range(5):
        (tmp_path / f"{model_file}.bak_2026010{i}_000000").write_text("x")

    RetrainingService._cleanup_old_versions("p1")

    remaining = sorted(tmp_path.glob(f"{model_file}.bak_*"))
    assert len(remaining) == mr.MAX_MODEL_VERSIONS


def test_cleanup_old_versions_unknown_name_is_noop(tmp_path, monkeypatch):
    monkeypatch.setattr(mr, "MODELS_DIR", str(tmp_path))
    RetrainingService._cleanup_old_versions("not_a_model")  # must not raise


# ── _restore_backup ──────────────────────────────────────────────────────────

def test_restore_backup_with_none_path_is_noop(tmp_path):
    model_path = tmp_path / "model.pkl"
    RetrainingService._restore_backup(None, str(model_path))
    assert not model_path.exists()


def test_restore_backup_renames_back(tmp_path):
    model_path = tmp_path / "model.pkl"
    backup_path = tmp_path / "model.pkl.bak_x"
    backup_path.write_text("backed-up")

    RetrainingService._restore_backup(str(backup_path), str(model_path))

    assert model_path.exists()
    assert not backup_path.exists()
    assert model_path.read_text() == "backed-up"


# ── _extract_new_data_rows ───────────────────────────────────────────────────

def _fake_row(intervention_id, failure_type, machine_id=1):
    intervention = SimpleNamespace(
        id=intervention_id, actual_failure_type=failure_type,
        machine_id=machine_id, priority="MOYENNE",
    )
    log = SimpleNamespace(
        air_temperature=300.0, process_temperature=310.0, rotational_speed=1500,
        torque=40.0, tool_wear=50, created_at="2026-01-01",
    )
    return intervention, log


def test_extract_new_data_rows_dedupes_by_intervention_id():
    rows = [_fake_row(1, "NONE"), _fake_row(1, "NONE"), _fake_row(2, "TWF")]

    new_data, interventions_to_update = RetrainingService._extract_new_data_rows(rows)

    assert interventions_to_update == [1, 2]
    assert len(new_data) == 2
    assert new_data[0][mr._COL_MACHINE_FAILURE] == 0
    assert new_data[1][mr._COL_MACHINE_FAILURE] == 1


def test_extract_new_data_rows_empty():
    new_data, interventions_to_update = RetrainingService._extract_new_data_rows([])
    assert new_data == []
    assert interventions_to_update == []


# ── _align_training_features ─────────────────────────────────────────────────

def _base_df(n=4):
    return pd.DataFrame({col: [1.0] * n for col in mr._BASE_COLUMNS})


def test_align_training_features_non_p3_derives_xgb_names():
    train_df = _base_df()
    val_df = _base_df()
    existing_data = {"features": mr._BASE_COLUMNS, "xgb_features": None}

    X, x_val, existing_features, xgb_features = RetrainingService._align_training_features(
        "p1", existing_data, train_df, val_df
    )

    assert existing_features == mr._BASE_COLUMNS
    assert xgb_features is not None
    assert "[" not in "".join(xgb_features)
    assert list(X.columns) == xgb_features
    assert list(x_val.columns) == xgb_features


def test_align_training_features_reuses_stored_xgb_features():
    train_df = _base_df()
    val_df = _base_df()
    stored_names = ["a", "b", "c", "d", "e"]
    existing_data = {"features": mr._BASE_COLUMNS, "xgb_features": stored_names}

    X, x_val, existing_features, xgb_features = RetrainingService._align_training_features(
        "p1", existing_data, train_df, val_df
    )

    assert xgb_features == stored_names
    assert list(X.columns) == stored_names


def test_align_training_features_p3_forces_extended_feature_set():
    extra_cols = [
        "temp_delta", "rpm_torque", "tool_wear_velocity",
        "process_temp_roll5_mean", "torque_roll5_mean", "rpm_roll5_mean",
    ]
    train_df = pd.DataFrame({col: [1.0] * 4 for col in mr._BASE_COLUMNS + extra_cols})
    val_df = train_df.copy()
    existing_data = {"features": [], "xgb_features": None}

    X, x_val, existing_features, xgb_features = RetrainingService._align_training_features(
        "p3", existing_data, train_df, val_df
    )

    assert existing_features == mr._BASE_COLUMNS + extra_cols
    assert len(xgb_features) == len(existing_features)
    assert X.shape[1] == len(existing_features)


# ── _group_holdout_split ─────────────────────────────────────────────────────

def test_group_holdout_split_with_multiple_machines():
    combined_df = pd.DataFrame({
        "machine_id": [1, 1, 2, 2, 3, 3],
        mr._COL_MACHINE_FAILURE: [0, 1, 0, 1, 0, 1],
    })

    train_df, val_df, machine_ids = RetrainingService._group_holdout_split(combined_df)

    assert machine_ids == [1, 2, 3]
    assert set(val_df["machine_id"].unique()) == {3}
    assert 3 not in train_df["machine_id"].unique()


def test_group_holdout_split_falls_back_to_random_split_under_two_machines():
    combined_df = pd.DataFrame({
        "machine_id": [1] * 10,
        mr._COL_MACHINE_FAILURE: [0, 1] * 5,
    })

    train_df, val_df, machine_ids = RetrainingService._group_holdout_split(combined_df)

    assert machine_ids == [1]
    assert len(train_df) + len(val_df) == len(combined_df)


def test_group_holdout_split_no_machine_id_column():
    combined_df = pd.DataFrame({mr._COL_MACHINE_FAILURE: [0, 1] * 5})

    train_df, val_df, machine_ids = RetrainingService._group_holdout_split(combined_df)

    assert machine_ids == []
    assert len(train_df) + len(val_df) == len(combined_df)


# ── _apply_repeated_holdout_metrics ──────────────────────────────────────────

def test_apply_repeated_holdout_metrics_skips_when_not_enough_machines():
    gate_metrics = {}
    RetrainingService._apply_repeated_holdout_metrics(
        "p2", gate_metrics, full_df=None, machine_ids=[1], existing_features=[],
        xgb_features=None, existing_data={},
    )
    assert gate_metrics == {}


def test_apply_repeated_holdout_metrics_skips_for_non_gated_model():
    gate_metrics = {}
    RetrainingService._apply_repeated_holdout_metrics(
        "p1", gate_metrics, full_df=pd.DataFrame(), machine_ids=[1, 2, 3],
        existing_features=[], xgb_features=None, existing_data={},
    )
    assert gate_metrics == {}
