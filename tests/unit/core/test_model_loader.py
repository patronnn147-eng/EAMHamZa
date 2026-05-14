import pytest
import joblib
from unittest.mock import patch, MagicMock
from pathlib import Path
from app.ml_microservice.src.core.model_loader import (
    load_p1, load_p2, load_p3, load_p4, load_p5, load_p6,
    startup_check, _extract, _load,
)


# ── _extract ────────────────────────────────────────────────────────────────

def test_extract_dict_returns_model_value():
    data = {"model": "my_model", "extra": "ignored"}
    assert _extract(data) == "my_model"


def test_extract_bare_model_returned_as_is():
    obj = object()
    assert _extract(obj) is obj


def test_extract_dict_missing_key_returns_none():
    assert _extract({"wrong_key": 1}) is None


# ── _load ────────────────────────────────────────────────────────────────────

def test_load_missing_file_returns_none(tmp_path):
    result = _load(tmp_path / "nonexistent.pkl", "TEST")
    assert result is None


def test_load_valid_pkl_returns_data(tmp_path):
    pkl = tmp_path / "model.pkl"
    joblib.dump({"model": "ok"}, pkl)
    result = _load(pkl, "TEST")
    assert result == {"model": "ok"}


def test_load_corrupt_pkl_returns_none(tmp_path):
    pkl = tmp_path / "corrupt.pkl"
    pkl.write_bytes(b"not a valid pickle")
    result = _load(pkl, "TEST")
    assert result is None


# ── load_p1 — cache ──────────────────────────────────────────────────────────

def test_load_p1_missing_file_returns_none():
    with patch("app.ml_microservice.src.core.model_loader.config") as mock_cfg:
        mock_cfg.models_dir = Path("/nonexistent/dir")
        load_p1.cache_clear()
        result = load_p1()
    assert result is None


def test_load_p1_cache_hit(tmp_path):
    """Second call returns same object without re-reading disk."""
    fake_model = {"type": "fake_p1_model"}
    pkl = tmp_path / "basic_machine_model.pkl"
    joblib.dump({"model": fake_model}, pkl)
    with patch("app.ml_microservice.src.core.model_loader.config") as mock_cfg:
        mock_cfg.models_dir = tmp_path
        load_p1.cache_clear()
        r1 = load_p1()
        r2 = load_p1()
    assert r1 is r2  # same object = cache hit


# ── load_p2 ──────────────────────────────────────────────────────────────────

def test_load_p2_missing_returns_none():
    with patch("app.ml_microservice.src.core.model_loader.config") as mock_cfg:
        mock_cfg.models_dir = Path("/nonexistent/dir")
        load_p2.cache_clear()
        result = load_p2()
    assert result is None


def test_load_p2_returns_model_and_labels(tmp_path):
    fake_model = {"type": "fake_p2_model"}
    joblib.dump({"model": fake_model, "labels": ["A", "B"]}, tmp_path / "ml_model_p2_failure_type.pkl")
    with patch("app.ml_microservice.src.core.model_loader.config") as mock_cfg:
        mock_cfg.models_dir = tmp_path
        load_p2.cache_clear()
        result = load_p2()
    assert result is not None
    assert "model" in result
    assert result["labels"] == ["A", "B"]


# ── startup_check ─────────────────────────────────────────────────────────────

def test_startup_check_runs_without_exception():
    """startup_check() must not raise even if all models are missing."""
    with patch("app.ml_microservice.src.core.model_loader.config") as mock_cfg:
        mock_cfg.models_dir = Path("/nonexistent/dir")
        for fn in [load_p1, load_p2, load_p3, load_p4, load_p5, load_p6]:
            fn.cache_clear()
        startup_check()  # must not raise
