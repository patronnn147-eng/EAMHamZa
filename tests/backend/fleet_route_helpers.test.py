"""Unit tests for the fleet dashboard helper functions in
app/backend/modules/ml/routes/fleet.py."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import modules.ml.routes.fleet as fleet_mod
from modules.ml.routes.fleet import (
    _fetch_interventions,
    _fleet_telemetry_by_machine,
    _fusion_from_log,
    _process_single_machine,
)


# ── _fusion_from_log ──────────────────────────────────────────────────────────

def test_fusion_from_log_none_returns_none():
    assert _fusion_from_log(None) is None


def test_fusion_from_log_builds_synthetic_fusion_dict():
    log = SimpleNamespace(
        failure_probability=42.5, rul_days=10.0, is_anomaly=True,
        anomaly_score=0.7, predicted_priority="P1",
    )
    result = _fusion_from_log(log)
    assert result["p1_failure_probability"] == 42.5
    assert result["p3_rul_days"] == 10.0
    assert result["p4_is_anomaly"] is True
    assert result["p5_predicted_priority"] == "P1"
    assert "unified_health_score" not in result  # degraded-mode marker


def test_fusion_from_log_handles_none_fields():
    log = SimpleNamespace(
        failure_probability=None, rul_days=None, is_anomaly=None,
        anomaly_score=None, predicted_priority=None,
    )
    result = _fusion_from_log(log)
    assert result["p1_failure_probability"] == 0.0
    assert result["p3_rul_days"] is None
    assert result["p4_is_anomaly"] is False


# ── _fetch_interventions ──────────────────────────────────────────────────────

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

    async def execute(self, *_args, **_kwargs):
        return self._results.pop(0)


@pytest.mark.asyncio
async def test_fetch_interventions_returns_rows():
    db = FakeDb([FakeScalarsResult(["itv1", "itv2"])])
    result = await _fetch_interventions(machine_id=1, db=db)
    assert result == ["itv1", "itv2"]


# ── _fleet_telemetry_by_machine ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fleet_telemetry_by_machine_groups_by_machine_id():
    entries = [
        SimpleNamespace(machine_id=1, recorded_at="t1"),
        SimpleNamespace(machine_id=2, recorded_at="t2"),
        SimpleNamespace(machine_id=1, recorded_at="t3"),
    ]
    db = FakeDb([FakeScalarsResult(entries)])
    result = await _fleet_telemetry_by_machine(db)
    assert len(result[1]) == 2
    assert len(result[2]) == 1


@pytest.mark.asyncio
async def test_fleet_telemetry_by_machine_caps_at_500():
    entries = [SimpleNamespace(machine_id=1, recorded_at=i) for i in range(600)]
    db = FakeDb([FakeScalarsResult(entries)])
    result = await _fleet_telemetry_by_machine(db)
    assert len(result[1]) == 500
    assert result[1][0].recorded_at == 100  # kept the last 500 (100..599)


# ── _process_single_machine ───────────────────────────────────────────────────

def _machine(mid=1, zone="Z1", sous_zone="SZ1", statut="OPERATIONNELLE"):
    return SimpleNamespace(
        id=mid, nom=f"M{mid}", zone=zone, sous_zone=sous_zone, statut=statut,
        date_derniere_maintenance=None, date_prochaine_maintenance=None,
    )


@pytest.mark.asyncio
async def test_process_single_machine_uses_prefetched_interventions():
    machine = _machine()
    db = FakeDb([])
    result = await _process_single_machine(
        machine, db, interventions_by_machine={1: []}, latest_logs_by_machine={},
        telemetry_by_machine={}, parts_readiness_map={1: "LOW"}, ml_available=False,
    )
    assert result["zone"] == "Z1"
    assert result["parts_ready"] == "LOW"


@pytest.mark.asyncio
async def test_process_single_machine_falls_back_when_no_telemetry():
    machine = _machine()
    db = FakeDb([])
    result = await _process_single_machine(
        machine, db, interventions_by_machine={1: []}, latest_logs_by_machine={},
        telemetry_by_machine={}, parts_readiness_map={}, ml_available=True,
    )
    assert result["parts_ready"] == "OK"  # default when not in map


@pytest.mark.asyncio
async def test_process_single_machine_uses_ml_client_when_telemetry_and_available(monkeypatch):
    machine = _machine()
    telemetry_entry = SimpleNamespace(
        air_temperature=300.0, process_temperature=310.0, rotational_speed=1500,
        torque=40.0, tool_wear=10.0, recorded_at=datetime.now(timezone.utc),
    )
    fake_predict = AsyncMock(return_value={"unified_health_score": 90.0})
    monkeypatch.setattr(fleet_mod.ml_client, "predict_all", fake_predict)
    db = FakeDb([])
    result = await _process_single_machine(
        machine, db, interventions_by_machine={1: []}, latest_logs_by_machine={},
        telemetry_by_machine={1: [telemetry_entry]}, parts_readiness_map={}, ml_available=True,
    )
    # health_score itself gets overridden to 100.0 by _compute_kpis' no-interventions
    # short-circuit (real, correct business logic) — what this test actually verifies
    # is that the live ml_client path was taken (score_source) rather than the
    # degraded _fusion_from_log fallback.
    fake_predict.assert_awaited_once()
    assert result["health_breakdown"]["score_source"] == "dst_fusion"


@pytest.mark.asyncio
async def test_process_single_machine_swallows_ml_client_exception(monkeypatch):
    machine = _machine()
    telemetry_entry = SimpleNamespace(
        air_temperature=300.0, process_temperature=310.0, rotational_speed=1500,
        torque=40.0, tool_wear=10.0, recorded_at=datetime.now(timezone.utc),
    )
    monkeypatch.setattr(
        fleet_mod.ml_client, "predict_all", AsyncMock(side_effect=RuntimeError("boom"))
    )
    db = FakeDb([])
    log = SimpleNamespace(
        failure_probability=10.0, rul_days=20.0, is_anomaly=False,
        anomaly_score=0.1, predicted_priority="P2",
    )
    result = await _process_single_machine(
        machine, db, interventions_by_machine={1: []}, latest_logs_by_machine={1: log},
        telemetry_by_machine={1: [telemetry_entry]}, parts_readiness_map={}, ml_available=True,
    )
    # Falls back to _fusion_from_log via the cached log, not a crash
    assert result["health_breakdown"]["score_source"] == "fallback_additive"
