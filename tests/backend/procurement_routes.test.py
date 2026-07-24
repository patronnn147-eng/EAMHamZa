"""Unit tests for the P7 KPI/queue route handlers in
app/backend/modules/ml/routes/procurement.py, called directly (bypassing
FastAPI/HTTP) with a fake AsyncSession."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from modules.ml.routes import procurement as procurement_mod
from modules.ml.routes.procurement import (
    approve_procurement_draft_endpoint,
    create_procurement_draft_endpoint,
    get_demand_forecast,
    get_machine_readiness,
    get_machine_timeline,
    get_p7_kpis,
    get_procurement_queue,
    quick_action_endpoint,
    refresh_demand_forecast,
    reject_procurement_draft_endpoint,
)


class FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value

    def all(self):
        return self._value

    def scalar_one_or_none(self):
        return self._value


class FakeDb:
    def __init__(self, execute_results):
        self._results = list(execute_results)
        self.committed = 0

    async def execute(self, *_a, **_k):
        return self._results.pop(0)

    async def commit(self):
        self.committed += 1


# ── get_p7_kpis ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_p7_kpis_computes_rates():
    db = FakeDb([
        FakeScalarResult(10),  # total_machines
        FakeScalarResult(2),   # shortage_count
        FakeScalarResult(7),   # predicted_machines
        FakeScalarResult(3),   # draft_count
    ])
    result = await get_p7_kpis(db)
    kpis = result["kpis"]
    assert kpis["stock_readiness_rate"] == 80.0  # (10-2)/10 * 100
    assert kpis["adoption_rate"] == 70.0  # 7/10 * 100
    assert kpis["active_shortages"] == 2
    assert kpis["draft_wos_pending"] == 3
    assert kpis["total_machines"] == 10


@pytest.mark.asyncio
async def test_get_p7_kpis_avoids_division_by_zero_with_no_machines():
    db = FakeDb([
        FakeScalarResult(None),  # total_machines -> defaults to 1 via `or 1`
        FakeScalarResult(0),
        FakeScalarResult(0),
        FakeScalarResult(0),
    ])
    result = await get_p7_kpis(db)
    assert result["kpis"]["total_machines"] == 1
    assert result["kpis"]["stock_readiness_rate"] == 100.0


# ── get_procurement_queue ─────────────────────────────────────────────────────

class _Row:
    def __init__(self, alert, machine):
        self.Alert = alert
        self.Machines = machine


@pytest.mark.asyncio
async def test_get_procurement_queue_maps_joined_rows():
    alert = SimpleNamespace(
        alert_id=1, machine_id=5, severity=SimpleNamespace(value="HIGH"),
        message="Low stock", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    machine = SimpleNamespace(nom="M5")
    db = FakeDb([FakeScalarResult([_Row(alert, machine)])])
    result = await get_procurement_queue(db)
    assert result["success"] is True
    assert result["count"] == 1
    assert result["items"][0]["machine_name"] == "M5"
    assert result["items"][0]["severity"] == "HIGH"
    assert result["items"][0]["created_at"] == "2026-01-01T00:00:00+00:00"


@pytest.mark.asyncio
async def test_get_procurement_queue_empty():
    db = FakeDb([FakeScalarResult([])])
    result = await get_procurement_queue(db)
    assert result == {"success": True, "count": 0, "items": []}


@pytest.mark.asyncio
async def test_get_procurement_queue_null_created_at():
    alert = SimpleNamespace(
        alert_id=1, machine_id=5, severity=SimpleNamespace(value="LOW"),
        message="msg", created_at=None,
    )
    machine = SimpleNamespace(nom="M5")
    db = FakeDb([FakeScalarResult([_Row(alert, machine)])])
    result = await get_procurement_queue(db)
    assert result["items"][0]["created_at"] is None


# ── get_demand_forecast / refresh_demand_forecast ──────────────────────────────

@pytest.mark.asyncio
async def test_get_demand_forecast_delegates(monkeypatch):
    forecast_mock = AsyncMock(return_value={"items": ["piece-1"]})
    monkeypatch.setattr("modules.ml.services.demand_forecast.compute_demand_forecast", forecast_mock)
    db = FakeDb([])
    result = await get_demand_forecast(horizon_days=60, limit=20, db=db)
    assert result == {"items": ["piece-1"]}
    forecast_mock.assert_awaited_once_with(db, horizon_days=60, limit=20)


@pytest.mark.asyncio
async def test_refresh_demand_forecast_invalidates_cache(monkeypatch):
    invalidate_mock = SimpleNamespace(called=False)

    def _invalidate():
        invalidate_mock.called = True

    monkeypatch.setattr("modules.ml.services.demand_forecast.invalidate_forecast_cache", _invalidate)
    result = await refresh_demand_forecast()
    assert invalidate_mock.called is True
    assert result == {"status": "cache_cleared", "message": "Demand forecast cache cleared."}


# ── get_machine_readiness ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_machine_readiness_not_found():
    db = FakeDb([FakeScalarResult(None)])
    with pytest.raises(HTTPException) as exc_info:
        await get_machine_readiness(machine_id=99, db=db)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_machine_readiness_no_prediction_log_uses_default_proxy(monkeypatch):
    machine = SimpleNamespace(id=1)
    db = FakeDb([FakeScalarResult(machine), FakeScalarResult(None)])
    captured = {}

    async def _fake_readiness(machine_id, health_proxy, arg3, db_arg):
        captured["health_proxy"] = health_proxy
        return {"score": 60}

    monkeypatch.setattr("modules.ml.services.readiness.get_readiness_for_machine", _fake_readiness)
    result = await get_machine_readiness(machine_id=1, db=db)
    assert captured["health_proxy"] == 50.0
    assert result == {"success": True, "machine_id": 1, "score": 60}


@pytest.mark.asyncio
async def test_get_machine_readiness_derives_proxy_from_prediction_log(monkeypatch):
    machine = SimpleNamespace(id=1)
    pred = SimpleNamespace(failure_probability=30.0)
    db = FakeDb([FakeScalarResult(machine), FakeScalarResult(pred)])
    captured = {}

    async def _fake_readiness(machine_id, health_proxy, arg3, db_arg):
        captured["health_proxy"] = health_proxy
        return {"score": 70}

    monkeypatch.setattr("modules.ml.services.readiness.get_readiness_for_machine", _fake_readiness)
    await get_machine_readiness(machine_id=1, db=db)
    assert captured["health_proxy"] == 70.0  # 100 - 30


# ── get_machine_timeline ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_machine_timeline_not_found():
    db = FakeDb([FakeScalarResult(None)])
    with pytest.raises(HTTPException) as exc_info:
        await get_machine_timeline(machine_id=99, limit=20, db=db)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_machine_timeline_success(monkeypatch):
    machine = SimpleNamespace(id=1)
    db = FakeDb([FakeScalarResult(machine)])
    monkeypatch.setattr(
        "modules.ml.services.readiness.get_timeline_for_machine",
        AsyncMock(return_value=[{"event": "maintenance"}]),
    )
    result = await get_machine_timeline(machine_id=1, limit=20, db=db)
    assert result["count"] == 1
    assert result["events"] == [{"event": "maintenance"}]


# ── create_procurement_draft_endpoint ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_procurement_draft_no_active_alert_404():
    db = FakeDb([FakeScalarResult(None)])
    user = SimpleNamespace(id=1)
    with pytest.raises(HTTPException) as exc_info:
        await create_procurement_draft_endpoint(machine_id=1, db=db, current_user=user)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_create_procurement_draft_already_exists():
    alert = SimpleNamespace(work_order_id=42)
    db = FakeDb([FakeScalarResult(alert)])
    user = SimpleNamespace(id=1)
    result = await create_procurement_draft_endpoint(machine_id=1, db=db, current_user=user)
    assert result == {"success": False, "message": "Draft already exists", "wo_id": 42}


@pytest.mark.asyncio
async def test_create_procurement_draft_success(monkeypatch):
    alert = SimpleNamespace(work_order_id=None)
    db = FakeDb([FakeScalarResult(alert)])
    user = SimpleNamespace(id=7)
    monkeypatch.setattr(
        "modules.ml.services.parts_drafts.create_procurement_draft",
        AsyncMock(return_value=101),
    )
    result = await create_procurement_draft_endpoint(machine_id=1, db=db, current_user=user)
    assert result["success"] is True
    assert result["wo_id"] == 101
    assert db.committed == 1


@pytest.mark.asyncio
async def test_create_procurement_draft_service_returns_none(monkeypatch):
    alert = SimpleNamespace(work_order_id=None)
    db = FakeDb([FakeScalarResult(alert)])
    user = SimpleNamespace(id=7)
    monkeypatch.setattr(
        "modules.ml.services.parts_drafts.create_procurement_draft",
        AsyncMock(return_value=None),
    )
    result = await create_procurement_draft_endpoint(machine_id=1, db=db, current_user=user)
    assert result["success"] is False
    assert db.committed == 0


# ── approve / reject procurement draft ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_approve_procurement_draft_delegates(monkeypatch):
    approve_mock = AsyncMock(return_value={"success": True, "statut": "SUBMITTED"})
    monkeypatch.setattr("modules.ml.services.parts_drafts.approve_procurement_draft", approve_mock)
    db = FakeDb([])
    user = SimpleNamespace(id=5)
    result = await approve_procurement_draft_endpoint(wo_id=10, db=db, current_user=user)
    assert result == {"success": True, "statut": "SUBMITTED"}
    approve_mock.assert_awaited_once_with(10, 5, db)


@pytest.mark.asyncio
async def test_reject_procurement_draft_delegates(monkeypatch):
    reject_mock = AsyncMock(return_value={"success": True, "statut": "ANNULÉ"})
    monkeypatch.setattr("modules.ml.services.parts_drafts.reject_procurement_draft", reject_mock)
    db = FakeDb([])
    result = await reject_procurement_draft_endpoint(wo_id=10, db=db)
    assert result == {"success": True, "statut": "ANNULÉ"}
    reject_mock.assert_awaited_once_with(10, db)


# ── quick_action_endpoint ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_quick_action_non_admin_rejected():
    db = FakeDb([])
    user = SimpleNamespace(id=1, role="TECHNICIEN")
    with pytest.raises(HTTPException) as exc_info:
        await quick_action_endpoint(machine_id=1, dry_run=False, db=db, current_user=user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_quick_action_admin_string_role_delegates(monkeypatch):
    db = FakeDb([])
    user = SimpleNamespace(id=1, role="ADMIN")
    monkeypatch.setattr(procurement_mod, "get_unified_health", AsyncMock(return_value={"parts_demand": {"items": []}}))
    provision_mock = AsyncMock(return_value={"success": True, "provisioned": 0})
    monkeypatch.setattr("modules.ml.services.quick_action.quick_provision_parts", provision_mock)

    result = await quick_action_endpoint(machine_id=1, dry_run=True, db=db, current_user=user)

    assert result == {"success": True, "provisioned": 0}
    provision_mock.assert_awaited_once_with(
        machine_id=1, actor_user_id=1, db=db, parts_demand={"items": []}, dry_run=True,
    )


@pytest.mark.asyncio
async def test_quick_action_admin_enum_role_delegates(monkeypatch):
    db = FakeDb([])
    user = SimpleNamespace(id=2, role=SimpleNamespace(value="ADMIN"))
    monkeypatch.setattr(procurement_mod, "get_unified_health", AsyncMock(return_value=None))
    provision_mock = AsyncMock(return_value={"success": True})
    monkeypatch.setattr("modules.ml.services.quick_action.quick_provision_parts", provision_mock)

    result = await quick_action_endpoint(machine_id=1, dry_run=False, db=db, current_user=user)

    assert result == {"success": True}
    provision_mock.assert_awaited_once_with(
        machine_id=1, actor_user_id=2, db=db, parts_demand=None, dry_run=False,
    )
