"""Unit tests for the fleet dashboard/critical route handlers in
app/backend/modules/ml/routes/fleet.py (not the per-machine helpers,
see fleet_route_helpers.test.py for those)."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import modules.ml.routes.fleet as fleet_mod
from modules.ml.routes.fleet import (
    get_fleet_critical_predictions,
    get_fleet_dashboard,
    refresh_fleet_dashboard,
)


@pytest.fixture(autouse=True)
def _reset_fleet_cache():
    fleet_mod._fleet_cache["data"] = None
    fleet_mod._fleet_cache["timestamp"] = None
    yield
    fleet_mod._fleet_cache["data"] = None
    fleet_mod._fleet_cache["timestamp"] = None


class FakeScalarsResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class FakeDb:
    def __init__(self, execute_results):
        self._results = list(execute_results)

    async def execute(self, *_a, **_k):
        return self._results.pop(0)


def _machine(mid=1, zone="Z1"):
    return SimpleNamespace(id=mid, nom=f"M{mid}", zone=zone, sous_zone="SZ", statut="OPERATIONNELLE")


# ── get_fleet_critical_predictions ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_fleet_critical_predictions_filters_and_sorts(monkeypatch):
    m1, m2, m3 = _machine(1), _machine(2), _machine(3)
    db = FakeDb([FakeScalarsResult([m1, m2, m3]), FakeScalarsResult([])])

    def _fake_calculate_rul(machine, interventions):
        by_id = {1: {"risk_level": "LOW", "rul_days": 5}, 2: {"risk_level": "CRITICAL", "rul_days": 2}, 3: {"risk_level": "HIGH", "rul_days": 8}}
        return by_id[machine.id]

    monkeypatch.setattr(fleet_mod.RULCalculator, "calculate_rul", _fake_calculate_rul)
    result = await get_fleet_critical_predictions(db)
    risk_levels = [m["risk_level"] for m in result["machines"]]
    assert risk_levels == ["CRITICAL", "HIGH"]  # LOW excluded
    assert [m["rul_days"] for m in result["machines"]] == [2, 8]  # sorted ascending


@pytest.mark.asyncio
async def test_get_fleet_critical_predictions_groups_interventions_by_machine(monkeypatch):
    m1 = _machine(1)
    itv_m1 = SimpleNamespace(machine_id=1)
    itv_other = SimpleNamespace(machine_id=99)
    db = FakeDb([FakeScalarsResult([m1]), FakeScalarsResult([itv_m1, itv_other])])

    captured = {}

    def _fake_calculate_rul(machine, interventions):
        captured["interventions"] = interventions
        return {"risk_level": "LOW", "rul_days": 1}

    monkeypatch.setattr(fleet_mod.RULCalculator, "calculate_rul", _fake_calculate_rul)
    await get_fleet_critical_predictions(db)
    assert captured["interventions"] == [itv_m1]  # only machine 1's intervention


# ── get_fleet_dashboard ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_fleet_dashboard_returns_cached_data_without_db_calls():
    fleet_mod._fleet_cache["data"] = [{"cached": True}]
    fleet_mod._fleet_cache["timestamp"] = datetime.now(timezone.utc)
    db = FakeDb([])  # would raise IndexError if execute is called
    result = await get_fleet_dashboard(db)
    assert result == [{"cached": True}]


@pytest.mark.asyncio
async def test_get_fleet_dashboard_rebuilds_when_cache_expired(monkeypatch):
    fleet_mod._fleet_cache["data"] = [{"stale": True}]
    fleet_mod._fleet_cache["timestamp"] = datetime.now(timezone.utc) - timedelta(seconds=999)
    db = FakeDb([
        FakeScalarsResult([]),  # machines
        FakeScalarsResult([]),  # interventions
        FakeScalarsResult([]),  # latest logs
        FakeScalarsResult([]),  # telemetry
    ])
    monkeypatch.setattr(fleet_mod, "batch_get_parts_readiness", AsyncMock(return_value={}))
    monkeypatch.setattr(fleet_mod, "is_ml_service_available", AsyncMock(return_value=True))
    result = await get_fleet_dashboard(db)
    assert result == []
    assert fleet_mod._fleet_cache["data"] == []


@pytest.mark.asyncio
async def test_get_fleet_dashboard_swallows_parts_readiness_failure(monkeypatch):
    db = FakeDb([
        FakeScalarsResult([]), FakeScalarsResult([]), FakeScalarsResult([]), FakeScalarsResult([]),
    ])
    monkeypatch.setattr(fleet_mod, "batch_get_parts_readiness", AsyncMock(side_effect=RuntimeError("db down")))
    monkeypatch.setattr(fleet_mod, "is_ml_service_available", AsyncMock(return_value=True))
    result = await get_fleet_dashboard(db)
    assert result == []


@pytest.mark.asyncio
async def test_get_fleet_dashboard_swallows_ml_availability_check_failure(monkeypatch):
    db = FakeDb([
        FakeScalarsResult([]), FakeScalarsResult([]), FakeScalarsResult([]), FakeScalarsResult([]),
    ])
    monkeypatch.setattr(fleet_mod, "batch_get_parts_readiness", AsyncMock(return_value={}))
    monkeypatch.setattr(fleet_mod, "is_ml_service_available", AsyncMock(side_effect=RuntimeError("ml down")))
    result = await get_fleet_dashboard(db)
    assert result == []


@pytest.mark.asyncio
async def test_get_fleet_dashboard_filters_errors_and_sorts_by_risk(monkeypatch):
    machines = [_machine(1), _machine(2), _machine(3)]
    db = FakeDb([
        FakeScalarsResult(machines), FakeScalarsResult([]), FakeScalarsResult([]), FakeScalarsResult([]),
    ])
    monkeypatch.setattr(fleet_mod, "batch_get_parts_readiness", AsyncMock(return_value={}))
    monkeypatch.setattr(fleet_mod, "is_ml_service_available", AsyncMock(return_value=True))

    results_by_id = {
        1: {"risk_level": "LOW", "rul_days": 10},
        2: {"risk_level": "CRITICAL", "rul_days": 3},
    }

    async def _fake_process(machine, *args, **kwargs):
        if machine.id == 3:
            raise RuntimeError("processing failed")
        return results_by_id[machine.id]

    monkeypatch.setattr(fleet_mod, "_process_single_machine", _fake_process)

    result = await get_fleet_dashboard(db)

    # machine 3's failure is filtered out; remaining sorted CRITICAL before LOW
    assert [r["risk_level"] for r in result] == ["CRITICAL", "LOW"]


# ── refresh_fleet_dashboard ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_fleet_dashboard_clears_cache():
    fleet_mod._fleet_cache["data"] = [{"old": True}]
    fleet_mod._fleet_cache["timestamp"] = datetime.now(timezone.utc)
    result = await refresh_fleet_dashboard()
    assert fleet_mod._fleet_cache["data"] is None
    assert fleet_mod._fleet_cache["timestamp"] is None
    assert result["status"] == "cache_cleared"
