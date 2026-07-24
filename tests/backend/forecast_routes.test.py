"""Unit tests for app/backend/modules/ml/routes/forecast.py route handlers
and the _require_planner guard in _common.py, called directly with fakes."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

import modules.ml.routes.forecast as forecast_mod
from modules.ml.routes._common import _require_planner
from modules.ml.routes.forecast import (
    _open_wo_count,
    _technician_count,
    get_forecast_budget,
    get_forecast_downtime,
    get_forecast_labor,
    get_forecast_summary,
    get_my_schedule,
    post_optimize_schedule,
)


class FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one(self):
        return self._value


class FakeDb:
    def __init__(self, execute_results):
        self._results = list(execute_results)

    async def execute(self, *_a, **_k):
        return self._results.pop(0)


def _user(role="ADMIN"):
    return SimpleNamespace(role=SimpleNamespace(value=role) if role else None, id=1)


# ── _require_planner ──────────────────────────────────────────────────────────

def test_require_planner_allows_admin():
    _require_planner(_user("ADMIN"))  # must not raise


def test_require_planner_allows_cheftech():
    _require_planner(_user("CHEFTECH"))  # must not raise


def test_require_planner_rejects_technicien():
    with pytest.raises(HTTPException) as exc_info:
        _require_planner(_user("TECHNICIEN"))
    assert exc_info.value.status_code == 403


def test_require_planner_rejects_no_role():
    with pytest.raises(HTTPException):
        _require_planner(SimpleNamespace(role=None))


# ── _open_wo_count / _technician_count ────────────────────────────────────────

@pytest.mark.asyncio
async def test_open_wo_count_returns_scalar():
    db = FakeDb([FakeScalarResult(7)])
    assert await _open_wo_count(db) == 7


@pytest.mark.asyncio
async def test_open_wo_count_none_becomes_zero():
    db = FakeDb([FakeScalarResult(None)])
    assert await _open_wo_count(db) == 0


@pytest.mark.asyncio
async def test_technician_count_returns_scalar():
    db = FakeDb([FakeScalarResult(4)])
    assert await _technician_count(db) == 4


# ── get_forecast_downtime (invalid horizon / role guard) ─────────────────────

@pytest.mark.asyncio
async def test_get_forecast_downtime_rejects_non_planner():
    with pytest.raises(HTTPException) as exc_info:
        await get_forecast_downtime(horizon=30, db=FakeDb([]), current_user=_user("TECHNICIEN"))
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_forecast_downtime_rejects_invalid_horizon():
    with pytest.raises(HTTPException) as exc_info:
        await get_forecast_downtime(horizon=99, db=FakeDb([]), current_user=_user("ADMIN"))
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_get_forecast_downtime_success(monkeypatch):
    monkeypatch.setattr(
        "modules.ml.services.downtime_forecast.compute_fleet_downtime",
        AsyncMock(return_value={"total_expected_hours": 12.0, "machines": []}),
    )
    result = await get_forecast_downtime(horizon=7, db=FakeDb([]), current_user=_user("ADMIN"))
    assert result["total_expected_hours"] == 12.0


# ── get_forecast_summary (cache) ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_forecast_summary_returns_cached_data_when_fresh():
    forecast_mod._FORECAST_SUMMARY_CACHE["data"] = {"downtime_hours": 5.0}
    forecast_mod._FORECAST_SUMMARY_CACHE["ts"] = datetime.now(timezone.utc)
    forecast_mod._FORECAST_SUMMARY_CACHE["ttl"] = 1800
    try:
        result = await get_forecast_summary(db=FakeDb([]), current_user=_user("ADMIN"))
        assert result == {"downtime_hours": 5.0}
    finally:
        forecast_mod._FORECAST_SUMMARY_CACHE["data"] = None
        forecast_mod._FORECAST_SUMMARY_CACHE["ts"] = None


@pytest.mark.asyncio
async def test_get_forecast_summary_recomputes_when_cache_expired(monkeypatch):
    forecast_mod._FORECAST_SUMMARY_CACHE["data"] = {"downtime_hours": 999.0}
    forecast_mod._FORECAST_SUMMARY_CACHE["ts"] = datetime.now(timezone.utc) - timedelta(hours=1)
    forecast_mod._FORECAST_SUMMARY_CACHE["ttl"] = 1800
    monkeypatch.setattr(
        "modules.ml.services.downtime_forecast.compute_fleet_downtime",
        AsyncMock(return_value={"total_expected_hours": 3.0, "machines": []}),
    )
    monkeypatch.setattr(
        "modules.ml.services.labor_forecast.forecast_labor",
        lambda **kwargs: {"demand_hours": 10.0, "overload": False},
    )
    monkeypatch.setattr(
        "modules.ml.services.demand_forecast.compute_demand_forecast",
        AsyncMock(return_value={"items": []}),
    )
    monkeypatch.setattr(
        "modules.ml.services.budget_forecast.forecast_budget",
        lambda **kwargs: {"total": 500.0},
    )
    db = FakeDb([FakeScalarResult(2), FakeScalarResult(1)])
    try:
        result = await get_forecast_summary(db=db, current_user=_user("ADMIN"))
        assert result["downtime_hours"] == 3.0
        assert result["labor_demand_hours"] == 10.0
        assert result["budget_total"] == 500.0
    finally:
        forecast_mod._FORECAST_SUMMARY_CACHE["data"] = None
        forecast_mod._FORECAST_SUMMARY_CACHE["ts"] = None


# ── get_forecast_labor ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_forecast_labor_rejects_non_planner():
    with pytest.raises(HTTPException) as exc_info:
        await get_forecast_labor(horizon=30, db=FakeDb([]), current_user=_user("TECHNICIEN"))
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_forecast_labor_rejects_invalid_horizon():
    with pytest.raises(HTTPException) as exc_info:
        await get_forecast_labor(horizon=99, db=FakeDb([]), current_user=_user("ADMIN"))
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_get_forecast_labor_success(monkeypatch):
    monkeypatch.setattr(
        "modules.ml.services.downtime_forecast.compute_fleet_downtime",
        AsyncMock(return_value={"total_expected_hours": 12.0, "machines": ["m1"]}),
    )
    monkeypatch.setattr(
        "modules.ml.services.labor_forecast.forecast_labor",
        lambda machines, open_wo, hours, techs, horizon: {"demand_hours": 20.0, "overload": True},
    )
    db = FakeDb([FakeScalarResult(3), FakeScalarResult(2)])
    result = await get_forecast_labor(horizon=30, db=db, current_user=_user("CHEFTECH"))
    assert result == {"demand_hours": 20.0, "overload": True}


# ── get_forecast_budget ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_forecast_budget_rejects_non_planner():
    with pytest.raises(HTTPException) as exc_info:
        await get_forecast_budget(horizon=30, db=FakeDb([]), current_user=_user("TECHNICIEN"))
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_forecast_budget_rejects_invalid_horizon():
    with pytest.raises(HTTPException) as exc_info:
        await get_forecast_budget(horizon=99, db=FakeDb([]), current_user=_user("ADMIN"))
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_get_forecast_budget_success(monkeypatch):
    monkeypatch.setattr(
        "modules.ml.services.downtime_forecast.compute_fleet_downtime",
        AsyncMock(return_value={"total_expected_hours": 12.0, "machines": []}),
    )
    monkeypatch.setattr(
        "modules.ml.services.labor_forecast.forecast_labor",
        lambda machines, open_wo, hours, techs, horizon: {"demand_hours": 15.0},
    )
    monkeypatch.setattr(
        "modules.ml.services.demand_forecast.compute_demand_forecast",
        AsyncMock(return_value={"items": [{"piece": "belt"}]}),
    )
    monkeypatch.setattr(
        "modules.ml.services.budget_forecast.forecast_budget",
        lambda labor_demand_hours, parts_reorder_items: {"total": 750.0, "items": parts_reorder_items},
    )
    db = FakeDb([FakeScalarResult(3), FakeScalarResult(2)])
    result = await get_forecast_budget(horizon=60, db=db, current_user=_user("ADMIN"))
    assert result["total"] == 750.0
    assert result["items"] == [{"piece": "belt"}]


# ── post_optimize_schedule ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_post_optimize_schedule_rejects_non_planner():
    with pytest.raises(HTTPException) as exc_info:
        await post_optimize_schedule(horizon=30, db=FakeDb([]), current_user=_user("TECHNICIEN"))
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_post_optimize_schedule_rejects_invalid_horizon():
    with pytest.raises(HTTPException) as exc_info:
        await post_optimize_schedule(horizon=99, db=FakeDb([]), current_user=_user("ADMIN"))
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_post_optimize_schedule_success(monkeypatch):
    monkeypatch.setattr(
        "modules.ml.services.schedule_optimizer.compute_schedule",
        AsyncMock(return_value={"solved": True, "assignments": []}),
    )
    result = await post_optimize_schedule(horizon=7, db=FakeDb([]), current_user=_user("CHEFTECH"))
    assert result["solved"] is True


# ── get_my_schedule ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_my_schedule_filters_to_current_technician(monkeypatch):
    schedule = {
        "assignments": [{"technician_id": 1, "wo": "A"}, {"technician_id": 2, "wo": "B"}],
        "solved": True, "fallback": False,
    }
    monkeypatch.setattr(
        "modules.ml.services.schedule_optimizer.compute_schedule",
        AsyncMock(return_value=schedule),
    )
    result = await get_my_schedule(db=FakeDb([]), current_user=_user("TECHNICIEN"))
    assert len(result["assignments"]) == 1
    assert result["assignments"][0]["wo"] == "A"
    assert result["technician_id"] == 1
    assert result["solved"] is True
