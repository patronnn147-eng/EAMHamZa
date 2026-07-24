"""Unit tests for app/backend/modules/ml/routes/predictions.py route handlers."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from modules.ml.routes import predictions as predictions_mod
from modules.ml.routes.predictions import (
    get_failure_probability,
    get_failure_type,
    get_machine_prediction,
)


class FakeScalars:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class FakeResult:
    def __init__(self, scalar_one_or_none=None, scalars_list=None, scalar_value=None):
        self._soo = scalar_one_or_none
        self._scalars_list = scalars_list
        self._scalar_value = scalar_value

    def scalar_one_or_none(self):
        return self._soo

    def scalars(self):
        return FakeScalars(self._scalars_list or [])

    def scalar(self):
        return self._scalar_value


class FakeSession:
    def __init__(self, execute_results):
        self._results = list(execute_results)
        self.added = []
        self.committed = 0
        self.rolled_back = 0

    async def execute(self, *_a, **_k):
        return self._results.pop(0)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed += 1

    async def rollback(self):
        self.rolled_back += 1


def _machine(id=1, nom="M1"):
    return SimpleNamespace(id=id, nom=nom)


# ── get_machine_prediction ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_machine_prediction_not_found():
    db = FakeSession([FakeResult(scalar_one_or_none=None)])
    with pytest.raises(HTTPException) as exc_info:
        await get_machine_prediction(machine_id=99, db=db)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_machine_prediction_success_no_telemetry(monkeypatch):
    machine = _machine()
    db = FakeSession([
        FakeResult(scalar_one_or_none=machine),
        FakeResult(scalars_list=[]),
        FakeResult(scalar_value=0),
    ])
    monkeypatch.setattr(predictions_mod, "_get_telemetry_history", AsyncMock(return_value=([], [])))
    monkeypatch.setattr(predictions_mod.RULCalculator, "calculate_rul", lambda *a, **k: {"rul_days": 30})
    monkeypatch.setattr(predictions_mod.ShadowLogger, "create_shadow_log", lambda pred: SimpleNamespace())

    result = await get_machine_prediction(machine_id=1, db=db)

    assert result == {"rul_days": 30}
    assert db.committed == 1


@pytest.mark.asyncio
async def test_get_machine_prediction_calls_ml_service_when_telemetry_present(monkeypatch):
    machine = _machine()
    db = FakeSession([
        FakeResult(scalar_one_or_none=machine),
        FakeResult(scalars_list=[]),
        FakeResult(scalar_value=0),
    ])
    telemetry_entry = SimpleNamespace(
        air_temperature=300.0, process_temperature=310.0, rotational_speed=1500,
        torque=40.0, tool_wear=5.0,
    )
    monkeypatch.setattr(
        predictions_mod, "_get_telemetry_history",
        AsyncMock(return_value=([telemetry_entry], [{"machine_id": 1}])),
    )
    monkeypatch.setattr(predictions_mod, "is_ml_service_available", AsyncMock(return_value=True))
    predict_all_mock = AsyncMock(return_value={"unified_health_score": 80.0})
    monkeypatch.setattr(predictions_mod.ml_client, "predict_all", predict_all_mock)

    captured = {}

    def _fake_calculate_rul(machine, interventions, **kwargs):
        captured["fusion_result"] = kwargs.get("fusion_result")
        return {"rul_days": 20}

    monkeypatch.setattr(predictions_mod.RULCalculator, "calculate_rul", _fake_calculate_rul)
    monkeypatch.setattr(predictions_mod.ShadowLogger, "create_shadow_log", lambda pred: SimpleNamespace())

    result = await get_machine_prediction(machine_id=1, db=db)

    assert result == {"rul_days": 20}
    predict_all_mock.assert_awaited_once()
    assert captured["fusion_result"] == {"unified_health_score": 80.0}


@pytest.mark.asyncio
async def test_get_machine_prediction_ml_service_failure_is_swallowed(monkeypatch):
    machine = _machine()
    db = FakeSession([
        FakeResult(scalar_one_or_none=machine),
        FakeResult(scalars_list=[]),
        FakeResult(scalar_value=0),
    ])
    telemetry_entry = SimpleNamespace(
        air_temperature=300.0, process_temperature=310.0, rotational_speed=1500,
        torque=40.0, tool_wear=5.0,
    )
    monkeypatch.setattr(
        predictions_mod, "_get_telemetry_history",
        AsyncMock(return_value=([telemetry_entry], [])),
    )
    monkeypatch.setattr(
        predictions_mod, "is_ml_service_available",
        AsyncMock(side_effect=RuntimeError("ml down")),
    )

    captured = {}

    def _fake_calculate_rul(machine, interventions, **kwargs):
        captured["fusion_result"] = kwargs.get("fusion_result")
        return {"rul_days": 15}

    monkeypatch.setattr(predictions_mod.RULCalculator, "calculate_rul", _fake_calculate_rul)
    monkeypatch.setattr(predictions_mod.ShadowLogger, "create_shadow_log", lambda pred: SimpleNamespace())

    result = await get_machine_prediction(machine_id=1, db=db)

    assert result == {"rul_days": 15}
    assert captured["fusion_result"] is None


@pytest.mark.asyncio
async def test_get_machine_prediction_shadow_log_failure_is_non_fatal(monkeypatch):
    machine = _machine()
    db = FakeSession([
        FakeResult(scalar_one_or_none=machine),
        FakeResult(scalars_list=[]),
        FakeResult(scalar_value=0),
    ])
    monkeypatch.setattr(predictions_mod, "_get_telemetry_history", AsyncMock(return_value=([], [])))
    monkeypatch.setattr(predictions_mod.RULCalculator, "calculate_rul", lambda *a, **k: {"rul_days": 30})

    def _raise(pred):
        raise RuntimeError("logging failed")

    monkeypatch.setattr(predictions_mod.ShadowLogger, "create_shadow_log", _raise)

    result = await get_machine_prediction(machine_id=1, db=db)

    assert result == {"rul_days": 30}
    assert db.rolled_back == 1
    assert db.committed == 0


@pytest.mark.asyncio
async def test_get_machine_prediction_calculation_error_raises_500(monkeypatch):
    machine = _machine()
    db = FakeSession([
        FakeResult(scalar_one_or_none=machine),
        FakeResult(scalars_list=[]),
        FakeResult(scalar_value=0),
    ])
    monkeypatch.setattr(predictions_mod, "_get_telemetry_history", AsyncMock(return_value=([], [])))

    def _raise(*a, **k):
        raise ValueError("bad model state")

    monkeypatch.setattr(predictions_mod.RULCalculator, "calculate_rul", _raise)

    with pytest.raises(HTTPException) as exc_info:
        await get_machine_prediction(machine_id=1, db=db)
    assert exc_info.value.status_code == 500


# ── get_failure_probability ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_failure_probability_not_found():
    db = FakeSession([FakeResult(scalar_one_or_none=None)])
    with pytest.raises(HTTPException) as exc_info:
        await get_failure_probability(
            machine_id=99, air=300, process=310, rpm=1500, torque=40, wear=5, db=db,
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_failure_probability_success_top_level_key(monkeypatch):
    machine = _machine(nom="Press-1")
    db = FakeSession([FakeResult(scalar_one_or_none=machine)])
    monkeypatch.setattr(
        predictions_mod.ml_client, "predict_failure_probability",
        AsyncMock(return_value={"failure_probability": 65.0}),
    )
    result = await get_failure_probability(
        machine_id=1, air=300, process=310, rpm=1500, torque=40, wear=5, db=db,
    )
    assert result["failure_probability"] == 65.0
    assert result["risk_level"] == "HIGH_RISK"
    assert result["machine_name"] == "Press-1"


@pytest.mark.asyncio
async def test_get_failure_probability_falls_back_to_nested_key(monkeypatch):
    machine = _machine()
    db = FakeSession([FakeResult(scalar_one_or_none=machine)])
    monkeypatch.setattr(
        predictions_mod.ml_client, "predict_failure_probability",
        AsyncMock(return_value={"prediction": {"failure_probability": 20.0}}),
    )
    result = await get_failure_probability(
        machine_id=1, air=300, process=310, rpm=1500, torque=40, wear=5, db=db,
    )
    assert result["failure_probability"] == 20.0
    assert result["risk_level"] == "LOW_RISK"


@pytest.mark.asyncio
async def test_get_failure_probability_ml_client_failure_defaults_to_zero(monkeypatch):
    machine = _machine()
    db = FakeSession([FakeResult(scalar_one_or_none=machine)])
    monkeypatch.setattr(
        predictions_mod.ml_client, "predict_failure_probability",
        AsyncMock(side_effect=RuntimeError("ml down")),
    )
    result = await get_failure_probability(
        machine_id=1, air=300, process=310, rpm=1500, torque=40, wear=5, db=db,
    )
    assert result["failure_probability"] == 0.0
    assert result["risk_level"] == "LOW_RISK"


# ── get_failure_type ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_failure_type_not_found():
    db = FakeSession([FakeResult(scalar_one_or_none=None)])
    with pytest.raises(HTTPException) as exc_info:
        await get_failure_type(
            machine_id=99, air=300, process=310, rpm=1500, torque=40, wear=5, db=db,
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_failure_type_success(monkeypatch):
    machine = _machine(nom="Lathe-2")
    db = FakeSession([FakeResult(scalar_one_or_none=machine)])
    monkeypatch.setattr(
        predictions_mod.ml_client, "predict_failure_type",
        AsyncMock(return_value={"failure_types": {"TWF": {"detected": True, "probability": 80.0}}}),
    )
    result = await get_failure_type(
        machine_id=1, air=300, process=310, rpm=1500, torque=40, wear=5, db=db,
    )
    assert result["failure_types"]["TWF"]["detected"] is True
    assert result["machine_name"] == "Lathe-2"


@pytest.mark.asyncio
async def test_get_failure_type_ml_client_failure_defaults_to_empty(monkeypatch):
    machine = _machine()
    db = FakeSession([FakeResult(scalar_one_or_none=machine)])
    monkeypatch.setattr(
        predictions_mod.ml_client, "predict_failure_type",
        AsyncMock(side_effect=RuntimeError("ml down")),
    )
    result = await get_failure_type(
        machine_id=1, air=300, process=310, rpm=1500, torque=40, wear=5, db=db,
    )
    assert result["failure_types"] == {}
