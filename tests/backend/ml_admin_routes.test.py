"""Unit tests for app/backend/modules/ml/routes/admin.py route handlers."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

import modules.ml.routes.admin as admin_mod
from modules.ml.routes.admin import (
    _drift_rows,
    get_ml_model_metrics,
    get_retraining_stats,
    ml_service_status,
    model_health,
    trigger_retraining,
)


class FakeResult:
    def __init__(self, rows=None):
        self._rows = rows or []

    def all(self):
        return self._rows


class FakeDb:
    def __init__(self, execute_results=None):
        self._results = list(execute_results or [])

    async def execute(self, *_a, **_k):
        return self._results.pop(0)


def _admin_user():
    return SimpleNamespace(role=SimpleNamespace(value="ADMIN"))


def _non_admin_user():
    return SimpleNamespace(role=SimpleNamespace(value="TECHNICIEN"))


# ── get_retraining_stats ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_retraining_stats_delegates(monkeypatch):
    monkeypatch.setattr(
        admin_mod.RetrainingService, "get_retraining_stats",
        AsyncMock(return_value={"new_data_points": 42}),
    )
    result = await get_retraining_stats(db=FakeDb())
    assert result == {"new_data_points": 42}


# ── trigger_retraining ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_trigger_retraining_non_admin_rejected():
    with pytest.raises(HTTPException) as exc_info:
        await trigger_retraining(db=FakeDb(), current_user=_non_admin_user())
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_trigger_retraining_success_returns_pipeline_result(monkeypatch):
    monkeypatch.setattr(
        admin_mod.RetrainingService, "run_retraining_pipeline",
        AsyncMock(return_value={"status": "trained", "models": ["P1"]}),
    )
    result = await trigger_retraining(db=FakeDb(), current_user=_admin_user())
    assert result == {"status": "trained", "models": ["P1"]}


@pytest.mark.asyncio
async def test_trigger_retraining_none_result_uses_default_message(monkeypatch):
    monkeypatch.setattr(
        admin_mod.RetrainingService, "run_retraining_pipeline",
        AsyncMock(return_value=None),
    )
    result = await trigger_retraining(db=FakeDb(), current_user=_admin_user())
    assert result == {"status": "success", "message": "Retraining pipeline completed."}


@pytest.mark.asyncio
async def test_trigger_retraining_pipeline_failure_raises_500(monkeypatch):
    monkeypatch.setattr(
        admin_mod.RetrainingService, "run_retraining_pipeline",
        AsyncMock(side_effect=RuntimeError("pipeline exploded")),
    )
    with pytest.raises(HTTPException) as exc_info:
        await trigger_retraining(db=FakeDb(), current_user=_admin_user())
    assert exc_info.value.status_code == 500


# ── ml_service_status ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ml_service_status_available(monkeypatch):
    monkeypatch.setattr(admin_mod, "is_ml_service_available", AsyncMock(return_value=True))
    result = await ml_service_status()
    assert result["ml_service_available"] is True
    assert result["fallback"] == "ML Container"


@pytest.mark.asyncio
async def test_ml_service_status_unavailable(monkeypatch):
    monkeypatch.setattr(admin_mod, "is_ml_service_available", AsyncMock(return_value=False))
    result = await ml_service_status()
    assert result["ml_service_available"] is False
    assert result["fallback"] == "Local calculation"


# ── get_ml_model_metrics ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_ml_model_metrics_success(monkeypatch):
    monkeypatch.setattr(
        admin_mod, "get_model_metrics",
        AsyncMock(return_value={"success": True, "metrics": {"roc_auc": 0.9}}),
    )
    result = await get_ml_model_metrics()
    assert result["success"] is True
    assert result["model"] == "p1_failure"
    assert result["metrics"]["roc_auc"] == 0.9


@pytest.mark.asyncio
async def test_get_ml_model_metrics_failure(monkeypatch):
    monkeypatch.setattr(admin_mod, "get_model_metrics", AsyncMock(return_value={"success": False}))
    result = await get_ml_model_metrics()
    assert result["success"] is False
    assert "error" in result


# ── _drift_rows ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_drift_rows_zips_sensor_columns():
    sensors = admin_mod.SENSORS
    row = tuple(float(i) for i in range(len(sensors)))
    db = FakeDb([FakeResult(rows=[row])])
    result = await _drift_rows(db, start="2026-01-01", end="2026-02-01")
    assert len(result) == 1
    assert set(result[0].keys()) == set(sensors)


# ── model_health ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_model_health_non_admin_rejected():
    with pytest.raises(HTTPException) as exc_info:
        await model_health(db=FakeDb(), current_user=_non_admin_user())
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_model_health_success_path(monkeypatch):
    monkeypatch.setattr(admin_mod, "scan_models", lambda a, b: {"P1": "ok"})
    monkeypatch.setattr(admin_mod, "check_sync", lambda a, b: [])
    monkeypatch.setattr(admin_mod, "compute_drift", lambda baseline, recent: {"verdict": "stable", "sensors": {}})
    monkeypatch.setattr(admin_mod, "get_model_metrics", AsyncMock(return_value={"success": True}))
    monkeypatch.setattr(
        admin_mod.RetrainingService, "get_retraining_stats",
        AsyncMock(return_value={"new_data_points": 100}),
    )
    monkeypatch.setattr(admin_mod, "recommend_retraining", lambda ndp, verdict: {"should_retrain": True})

    db = FakeDb([FakeResult(rows=[]), FakeResult(rows=[])])
    result = await model_health(db=db, current_user=_admin_user())

    assert result["models"] == {"P1": "ok"}
    assert result["drift"]["verdict"] == "stable"
    assert result["retrain"] == {"should_retrain": True}


@pytest.mark.asyncio
async def test_model_health_drift_failure_falls_back_to_insufficient_data(monkeypatch):
    monkeypatch.setattr(admin_mod, "scan_models", lambda a, b: {})
    monkeypatch.setattr(admin_mod, "check_sync", lambda a, b: [])

    async def _raise(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr(admin_mod, "_drift_rows", _raise)
    monkeypatch.setattr(admin_mod, "get_model_metrics", AsyncMock(return_value={"success": True}))
    monkeypatch.setattr(
        admin_mod.RetrainingService, "get_retraining_stats",
        AsyncMock(return_value={"new_data_points": 0}),
    )
    monkeypatch.setattr(admin_mod, "recommend_retraining", lambda ndp, verdict: {"should_retrain": False})

    result = await model_health(db=FakeDb(), current_user=_admin_user())
    assert result["drift"] == {"verdict": "insufficient_data", "sensors": {}}


@pytest.mark.asyncio
async def test_model_health_metrics_and_stats_failures_swallowed(monkeypatch):
    monkeypatch.setattr(admin_mod, "scan_models", lambda a, b: {})
    monkeypatch.setattr(admin_mod, "check_sync", lambda a, b: [])
    monkeypatch.setattr(admin_mod, "compute_drift", lambda baseline, recent: {"verdict": "stable", "sensors": {}})
    monkeypatch.setattr(admin_mod, "get_model_metrics", AsyncMock(side_effect=RuntimeError("ml down")))
    monkeypatch.setattr(
        admin_mod.RetrainingService, "get_retraining_stats",
        AsyncMock(side_effect=RuntimeError("db down")),
    )
    captured = {}

    def _fake_recommend(ndp, verdict):
        captured["ndp"] = ndp
        return {"should_retrain": False}

    monkeypatch.setattr(admin_mod, "recommend_retraining", _fake_recommend)

    db = FakeDb([FakeResult(rows=[]), FakeResult(rows=[])])
    result = await model_health(db=db, current_user=_admin_user())

    assert result["metrics"] == {"success": False}
    assert captured["ndp"] == 0
