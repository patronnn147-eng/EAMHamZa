"""Unit tests for the get_unified_health helper functions in
app/backend/modules/ml/routes/health.py, extracted during the 2026-07
SonarQube cognitive-complexity refactor."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

import modules.ml.routes.health as health_mod
from modules.ml.routes.health import (
    TelemetryUpdate,
    _attach_parts_and_schedule,
    _attach_recovery,
    _attach_sensor_status,
    _build_uh_base_response,
    _count_open_work_orders,
    _enrich_parts_demand_with_real_stock,
    _fetch_machine_or_404,
    _reprice_part_item,
    _run_ml_fusion,
    _try_update_maintenance_schedule,
    update_machine_telemetry,
)


# ── _build_uh_base_response ───────────────────────────────────────────────────

def test_build_uh_base_response_no_telemetry():
    machine = SimpleNamespace(nom="M1")
    prediction = {"health_score": 50.0, "rul_days": 10.0}
    response = _build_uh_base_response(1, machine, prediction, None, (None,) * 5, telemetry_points=0)
    assert response["telemetry_available"] is False
    assert response["air_temperature"] is None
    assert response["maintenance_event"] is False


def test_build_uh_base_response_with_fusion_result():
    machine = SimpleNamespace(nom="M1")
    prediction = {"health_score": 80.0, "health_breakdown": {"score_source": "dst_fusion", "dst_verdict": "Healthy"}}
    fusion = {"kalman_hi": 75.0, "maintenance_event": True, "p4_anomaly_score": 0.3}
    response = _build_uh_base_response(1, machine, prediction, fusion, (300.0, 310.0, 1500, 40.0, 10.0), telemetry_points=5)
    assert response["telemetry_available"] is True
    assert response["kalman_hi"] == 75.0
    assert response["maintenance_event"] is True
    assert response["p4_anomaly_score"] == 0.3
    assert response["tool_wear"] == 10


# ── _fetch_machine_or_404 ─────────────────────────────────────────────────────

class FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalar(self):
        return self._value

    def scalars(self):
        return self

    def all(self):
        return self._value or []


class FakeDb:
    def __init__(self, execute_results):
        self._results = list(execute_results)
        self.committed = 0
        self.added = []

    async def execute(self, *_args, **_kwargs):
        return self._results.pop(0)

    async def commit(self):
        self.committed += 1

    def add(self, obj):
        self.added.append(obj)

    async def refresh(self, _obj):
        pass


@pytest.mark.asyncio
async def test_fetch_machine_or_404_found():
    machine = SimpleNamespace(id=1, nom="M1")
    db = FakeDb([FakeScalarResult(machine)])
    result = await _fetch_machine_or_404(1, db)
    assert result is machine


@pytest.mark.asyncio
async def test_fetch_machine_or_404_missing_raises_404():
    db = FakeDb([FakeScalarResult(None)])
    with pytest.raises(HTTPException) as exc_info:
        await _fetch_machine_or_404(1, db)
    assert exc_info.value.status_code == 404


# ── _count_open_work_orders ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_count_open_work_orders_returns_scalar():
    db = FakeDb([FakeScalarResult(3)])
    assert await _count_open_work_orders(1, db) == 3


@pytest.mark.asyncio
async def test_count_open_work_orders_none_becomes_zero():
    db = FakeDb([FakeScalarResult(None)])
    assert await _count_open_work_orders(1, db) == 0


# ── _try_update_maintenance_schedule ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_try_update_maintenance_schedule_none_days_is_noop():
    machine = SimpleNamespace(date_derniere_maintenance=None, date_prochaine_maintenance=None)
    db = FakeDb([])
    result = await _try_update_maintenance_schedule(machine, db, None)
    assert result is None
    assert db.committed == 0


@pytest.mark.asyncio
async def test_try_update_maintenance_schedule_positive_days_commits():
    machine = SimpleNamespace(date_derniere_maintenance=None, date_prochaine_maintenance=None)
    db = FakeDb([])
    result = await _try_update_maintenance_schedule(machine, db, 15.4)
    assert result == 15.4
    assert db.committed == 1
    assert machine.date_prochaine_maintenance is not None


@pytest.mark.asyncio
async def test_try_update_maintenance_schedule_negative_days_no_commit():
    machine = SimpleNamespace(date_derniere_maintenance=None, date_prochaine_maintenance=None)
    db = FakeDb([])
    result = await _try_update_maintenance_schedule(machine, db, -5.0)
    assert result == -5.0
    assert db.committed == 0


# ── _reprice_part_item / _enrich_parts_demand_with_real_stock ────────────────

def test_reprice_part_item_unknown_piece_leaves_item_untouched():
    item = {"piece_id": 999, "expected_qty": 10}
    _reprice_part_item(item, real_stock={}, horizon=30)
    assert "urgency_score" not in item


def test_reprice_part_item_computes_shortfall_and_urgency():
    item = {"piece_id": 1, "expected_qty": 10.0}
    real_stock = {1: {"name": "Bolt", "reference": "B-1", "min_stock": 5.0, "on_hand": 2.0}}
    _reprice_part_item(item, real_stock, horizon=30)
    assert item["on_hand"] == 2.0
    assert item["shortfall"] == 8.0
    assert item["urgency_score"] == 0.8
    assert item["name"] == "Bolt"


@pytest.mark.asyncio
async def test_enrich_parts_demand_no_piece_ids_returns_unchanged():
    parts_demand = {"items": [{"piece_id": None}]}
    db = FakeDb([])
    result = await _enrich_parts_demand_with_real_stock(parts_demand, db)
    assert result is parts_demand


@pytest.mark.asyncio
async def test_enrich_parts_demand_reprices_and_sorts_by_urgency():
    class Row:
        def __init__(self, id, name, reference, min_stock, quantity):
            self.id, self.name, self.reference, self.min_stock, self.quantity = (
                id, name, reference, min_stock, quantity
            )

    class FakeRowsResult:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return self._rows

    db = FakeDb([FakeRowsResult([Row(1, "Low urgency", "R1", 1.0, 100.0), Row(2, "High urgency", "R2", 5.0, 0.0)])])
    parts_demand = {
        "horizon_days": 30,
        "items": [
            {"piece_id": 1, "expected_qty": 1.0},
            {"piece_id": 2, "expected_qty": 10.0},
        ],
    }
    result = await _enrich_parts_demand_with_real_stock(parts_demand, db)
    assert result["items"][0]["piece_id"] == 2  # higher urgency sorted first


# ── _run_ml_fusion ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_ml_fusion_no_telemetry_returns_none(monkeypatch):
    result = await _run_ml_fusion([], [], (None,) * 5, machine_id=1)
    assert result is None


@pytest.mark.asyncio
async def test_run_ml_fusion_service_unavailable_returns_none(monkeypatch):
    monkeypatch.setattr(health_mod, "is_ml_service_available", AsyncMock(return_value=False))
    result = await _run_ml_fusion([1], [], (300.0, 310.0, 1500, 40.0, 10.0), machine_id=1)
    assert result is None


@pytest.mark.asyncio
async def test_run_ml_fusion_success(monkeypatch):
    monkeypatch.setattr(health_mod, "is_ml_service_available", AsyncMock(return_value=True))
    fake_predict = AsyncMock(return_value={"unified_health_score": 88.0})
    monkeypatch.setattr(health_mod.ml_client, "predict_all", fake_predict)
    result = await _run_ml_fusion([1], [], (300.0, 310.0, 1500, 40.0, 10.0), machine_id=1)
    assert result == {"unified_health_score": 88.0}
    fake_predict.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_ml_fusion_swallows_exceptions(monkeypatch):
    monkeypatch.setattr(health_mod, "is_ml_service_available", AsyncMock(side_effect=RuntimeError("boom")))
    result = await _run_ml_fusion([1], [], (300.0, 310.0, 1500, 40.0, 10.0), machine_id=1)
    assert result is None


# ── _attach_sensor_status ─────────────────────────────────────────────────────

def test_attach_sensor_status_skips_when_no_telemetry():
    response = {"telemetry_available": False}
    _attach_sensor_status(response, SimpleNamespace(type="X", nom="M1"))
    assert response["sensor_status"] == []


def test_attach_sensor_status_builds_when_telemetry_available(monkeypatch):
    monkeypatch.setattr(health_mod, "build_sensor_status", lambda t, n, sensors: [{"ok": True}])
    response = {"telemetry_available": True, "air_temperature": 300.0}
    _attach_sensor_status(response, SimpleNamespace(type="X", nom="M1"))
    assert response["sensor_status"] == [{"ok": True}]


def test_attach_sensor_status_swallows_build_errors(monkeypatch):
    def _boom(*_a, **_k):
        raise RuntimeError("boom")

    monkeypatch.setattr(health_mod, "build_sensor_status", _boom)
    response = {"telemetry_available": True}
    _attach_sensor_status(response, SimpleNamespace(type="X", nom="M1"))
    assert response["sensor_status"] == []


# ── _attach_recovery ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_attach_recovery_no_recovery_found(monkeypatch):
    fake_service_instance = SimpleNamespace(
        get_latest_recovery_for_machine=AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        "services.ml.recovery.PostMaintenanceRecoveryService",
        lambda db: fake_service_instance,
    )
    response = {"unified_health_score": 50.0}
    await _attach_recovery(response, machine_id=1, db=FakeDb([]))
    assert response["recovery"] is None


@pytest.mark.asyncio
async def test_attach_recovery_found_calls_to_dict(monkeypatch):
    fake_recovery = SimpleNamespace(to_dict=lambda: {"delta": 5})
    fake_service_instance = SimpleNamespace(
        get_latest_recovery_for_machine=AsyncMock(return_value=fake_recovery)
    )
    monkeypatch.setattr(
        "services.ml.recovery.PostMaintenanceRecoveryService",
        lambda db: fake_service_instance,
    )
    response = {"unified_health_score": 50.0}
    await _attach_recovery(response, machine_id=1, db=FakeDb([]))
    assert response["recovery"] == {"delta": 5}


@pytest.mark.asyncio
async def test_attach_recovery_swallows_exceptions(monkeypatch):
    monkeypatch.setattr(
        "services.ml.recovery.PostMaintenanceRecoveryService",
        lambda db: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    response = {}
    await _attach_recovery(response, machine_id=1, db=FakeDb([]))
    assert response["recovery"] is None


# ── _attach_parts_and_schedule ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_attach_parts_and_schedule_no_fusion_result(monkeypatch):
    monkeypatch.setattr(
        health_mod, "get_machine_parts_readiness", AsyncMock(return_value={"status": "OK"})
    )
    monkeypatch.setattr(
        "modules.ml.services.parts_alerts.emit_shortfall_alert", AsyncMock()
    )
    response = {}
    machine = SimpleNamespace(date_derniere_maintenance=None, date_prochaine_maintenance=None)
    db = FakeDb([])
    await _attach_parts_and_schedule(response, machine, None, machine_id=1, db=db)
    assert response["parts_readiness"] == {"status": "OK"}
    assert response["p6_schedule_days"] is None
    assert response["parts_demand"] is None


@pytest.mark.asyncio
async def test_attach_parts_and_schedule_inventory_error_falls_back(monkeypatch):
    monkeypatch.setattr(
        health_mod, "get_machine_parts_readiness", AsyncMock(side_effect=RuntimeError("boom"))
    )
    monkeypatch.setattr("modules.ml.services.parts_alerts.emit_shortfall_alert", AsyncMock())
    response = {}
    machine = SimpleNamespace(date_derniere_maintenance=None, date_prochaine_maintenance=None)
    db = FakeDb([])
    await _attach_parts_and_schedule(response, machine, None, machine_id=1, db=db)
    assert response["parts_readiness"] == {"status": "UNKNOWN", "error": "inventory_unavailable"}


@pytest.mark.asyncio
async def test_attach_parts_and_schedule_enriches_parts_demand_with_real_stock(monkeypatch):
    monkeypatch.setattr(
        health_mod, "get_machine_parts_readiness", AsyncMock(return_value={"status": "OK"})
    )
    monkeypatch.setattr("modules.ml.services.parts_alerts.emit_shortfall_alert", AsyncMock())
    enrich_mock = AsyncMock(return_value={"items": [{"piece_id": 1, "enriched": True}]})
    monkeypatch.setattr(health_mod, "_enrich_parts_demand_with_real_stock", enrich_mock)

    response = {}
    machine = SimpleNamespace(date_derniere_maintenance=None, date_prochaine_maintenance=None)
    fusion_result = {"p7_parts_demand": {"items": [{"piece_id": 1}]}, "p6_schedule_days": None}
    db = FakeDb([])
    await _attach_parts_and_schedule(response, machine, fusion_result, machine_id=1, db=db)

    enrich_mock.assert_awaited_once()
    assert response["parts_demand"] == {"items": [{"piece_id": 1, "enriched": True}]}


# ── update_machine_telemetry ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_machine_telemetry_machine_not_found():
    db = FakeDb([FakeScalarResult(None)])
    with pytest.raises(HTTPException) as exc_info:
        await update_machine_telemetry(1, TelemetryUpdate(), db)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_machine_telemetry_applies_defaults_for_missing_fields():
    machine = SimpleNamespace(id=1, nom="M1")
    db = FakeDb([FakeScalarResult(machine)])
    result = await update_machine_telemetry(1, TelemetryUpdate(), db)

    assert result["telemetry"]["air_temperature"] == 300.0
    assert result["telemetry"]["process_temperature"] == 310.0
    assert result["telemetry"]["rotational_speed"] == 1500
    assert result["telemetry"]["torque"] == 40.0
    assert result["telemetry"]["tool_wear"] == 0.0
    assert db.committed == 1
    assert len(db.added) == 1


@pytest.mark.asyncio
async def test_update_machine_telemetry_uses_provided_values():
    machine = SimpleNamespace(id=1, nom="M1")
    db = FakeDb([FakeScalarResult(machine)])
    data = TelemetryUpdate(
        air_temperature=295.5, process_temperature=305.0,
        rotational_speed=1800, torque=55.0, tool_wear=42,
    )
    result = await update_machine_telemetry(1, data, db)

    assert result["telemetry"]["air_temperature"] == 295.5
    assert result["telemetry"]["rotational_speed"] == 1800
    assert result["telemetry"]["tool_wear"] == 42
    assert result["machine_id"] == 1
