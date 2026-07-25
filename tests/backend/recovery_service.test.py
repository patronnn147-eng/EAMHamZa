"""Unit tests for app/backend/services/ml/recovery.py (PostMaintenanceRecoveryService)."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from models.alertes import Alert  # noqa: F401
from models.ordres_travail import OrdreStatut
from services.ml.recovery import PostMaintenanceRecoveryService


class FakeResult:
    def __init__(self, scalar_one_or_none=None, scalars_list=None):
        self._soo = scalar_one_or_none
        self._scalars_list = scalars_list

    def scalar_one_or_none(self):
        return self._soo

    def scalars(self):
        return self

    def all(self):
        return self._scalars_list or []


class FakeDb:
    def __init__(self, execute_results=None):
        self._results = list(execute_results or [])

    async def execute(self, *_a, **_k):
        return self._results.pop(0)


def _wo(**overrides):
    base = dict(
        id=1, machine_id=1, statut=OrdreStatut.COMPLETED,
        health_score_at_creation=None, health_score_at_completion=None, date_fin=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


# ── _days_since_completion ────────────────────────────────────────────────────

def test_days_since_completion_no_date_fin():
    days, within = PostMaintenanceRecoveryService._days_since_completion(_wo(date_fin=None))
    assert days is None
    assert within is False


def test_days_since_completion_recent_naive_datetime():
    recent = datetime.now(timezone.utc) - timedelta(days=2)
    days, within = PostMaintenanceRecoveryService._days_since_completion(
        _wo(date_fin=recent.replace(tzinfo=None))
    )
    assert days == 2
    assert within is True


def test_days_since_completion_outside_window():
    old = datetime.now(timezone.utc) - timedelta(days=30)
    days, within = PostMaintenanceRecoveryService._days_since_completion(_wo(date_fin=old))
    assert days == 30
    assert within is False


# ── _classify_status ──────────────────────────────────────────────────────────

def test_classify_status_not_completed_is_monitoring():
    assert PostMaintenanceRecoveryService._classify_status(False, 50.0, 10.0, 60.0) == "Monitoring"


def test_classify_status_no_baseline():
    assert PostMaintenanceRecoveryService._classify_status(True, None, None, 60.0) == "No baseline"


def test_classify_status_no_improvement():
    assert PostMaintenanceRecoveryService._classify_status(True, 50.0, 0.0, 50.0) == "No improvement"
    assert PostMaintenanceRecoveryService._classify_status(True, 50.0, -5.0, 45.0) == "No improvement"


def test_classify_status_recovered_above_threshold():
    assert PostMaintenanceRecoveryService._classify_status(True, 50.0, 30.0, 80.0) == "Recovered"


def test_classify_status_recovering_below_threshold():
    assert PostMaintenanceRecoveryService._classify_status(True, 50.0, 10.0, 60.0) == "Recovering"


# ── compute_recovery ──────────────────────────────────────────────────────────

def test_compute_recovery_full_recovered_case():
    svc = PostMaintenanceRecoveryService(FakeDb())
    recent = datetime.now(timezone.utc) - timedelta(days=1)
    wo = _wo(health_score_at_creation=50.0, health_score_at_completion=55.0, date_fin=recent)
    result = svc.compute_recovery(wo, current_score=80.0)
    assert result.delta == 30.0
    assert result.status == "Recovered"
    assert result.score_before == 50.0
    assert result.score_after_completion == 55.0
    assert result.current_score == 80.0
    assert result.within_recovery_window is True
    assert result.completion_date is not None


def test_compute_recovery_no_baseline_no_current_score():
    svc = PostMaintenanceRecoveryService(FakeDb())
    wo = _wo(health_score_at_creation=None)
    result = svc.compute_recovery(wo, current_score=None)
    assert result.delta is None
    assert result.status == "No baseline"
    assert result.current_score is None


def test_compute_recovery_not_completed_status_is_monitoring():
    svc = PostMaintenanceRecoveryService(FakeDb())
    wo = _wo(statut=OrdreStatut.IN_PROGRESS, health_score_at_creation=50.0)
    result = svc.compute_recovery(wo, current_score=60.0)
    assert result.status == "Monitoring"


def test_compute_recovery_to_dict_round_trips():
    svc = PostMaintenanceRecoveryService(FakeDb())
    wo = _wo(health_score_at_creation=50.0)
    result = svc.compute_recovery(wo, current_score=60.0)
    d = result.to_dict()
    assert d["work_order_id"] == 1
    assert d["delta"] == 10.0


# ── get_latest_recovery_for_machine ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_latest_recovery_no_work_order_returns_none():
    db = FakeDb([FakeResult(scalar_one_or_none=None)])
    svc = PostMaintenanceRecoveryService(db)
    assert await svc.get_latest_recovery_for_machine(1, current_score=60.0) is None


@pytest.mark.asyncio
async def test_get_latest_recovery_within_window_returns_result():
    recent = datetime.now(timezone.utc) - timedelta(days=1)
    wo = _wo(health_score_at_creation=50.0, date_fin=recent)
    db = FakeDb([FakeResult(scalar_one_or_none=wo)])
    svc = PostMaintenanceRecoveryService(db)
    result = await svc.get_latest_recovery_for_machine(1, current_score=70.0)
    assert result is not None
    assert result.delta == 20.0


@pytest.mark.asyncio
async def test_get_latest_recovery_suppressed_when_outside_window_and_no_baseline():
    old = datetime.now(timezone.utc) - timedelta(days=30)
    wo = _wo(health_score_at_creation=None, date_fin=old)
    db = FakeDb([FakeResult(scalar_one_or_none=wo)])
    svc = PostMaintenanceRecoveryService(db)
    assert await svc.get_latest_recovery_for_machine(1, current_score=70.0) is None


@pytest.mark.asyncio
async def test_get_latest_recovery_outside_window_but_has_baseline_still_returned():
    old = datetime.now(timezone.utc) - timedelta(days=30)
    wo = _wo(health_score_at_creation=50.0, date_fin=old)
    db = FakeDb([FakeResult(scalar_one_or_none=wo)])
    svc = PostMaintenanceRecoveryService(db)
    result = await svc.get_latest_recovery_for_machine(1, current_score=70.0)
    assert result is not None
    assert result.within_recovery_window is False


# ── snapshot_health ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_snapshot_health_returns_none_when_ml_service_unavailable(monkeypatch):
    monkeypatch.setattr("services.ml.recovery.is_ml_service_available", AsyncMock(return_value=False))
    svc = PostMaintenanceRecoveryService(FakeDb())
    assert await svc.snapshot_health(1) is None


@pytest.mark.asyncio
async def test_snapshot_health_uses_unified_health_score(monkeypatch):
    monkeypatch.setattr("services.ml.recovery.is_ml_service_available", AsyncMock(return_value=True))
    monkeypatch.setattr(
        "services.ml.recovery.ml_client.predict_all",
        AsyncMock(return_value={"unified_health_score": 77.777}),
    )
    db = FakeDb([FakeResult(scalar_one_or_none=None), FakeResult(scalars_list=[])])
    svc = PostMaintenanceRecoveryService(db)
    assert await svc.snapshot_health(1) == 77.78


@pytest.mark.asyncio
async def test_snapshot_health_falls_back_to_p1_failure_probability(monkeypatch):
    monkeypatch.setattr("services.ml.recovery.is_ml_service_available", AsyncMock(return_value=True))
    monkeypatch.setattr(
        "services.ml.recovery.ml_client.predict_all",
        AsyncMock(return_value={"p1_failure_probability": 20.0}),
    )
    db = FakeDb([FakeResult(scalar_one_or_none=None), FakeResult(scalars_list=[])])
    svc = PostMaintenanceRecoveryService(db)
    assert await svc.snapshot_health(1) == 80.0


@pytest.mark.asyncio
async def test_snapshot_health_returns_none_when_fusion_has_no_score_or_p1(monkeypatch):
    monkeypatch.setattr("services.ml.recovery.is_ml_service_available", AsyncMock(return_value=True))
    monkeypatch.setattr(
        "services.ml.recovery.ml_client.predict_all", AsyncMock(return_value={})
    )
    db = FakeDb([FakeResult(scalar_one_or_none=None), FakeResult(scalars_list=[])])
    svc = PostMaintenanceRecoveryService(db)
    assert await svc.snapshot_health(1) is None


@pytest.mark.asyncio
async def test_snapshot_health_returns_none_when_fusion_is_not_a_dict(monkeypatch):
    monkeypatch.setattr("services.ml.recovery.is_ml_service_available", AsyncMock(return_value=True))
    monkeypatch.setattr("services.ml.recovery.ml_client.predict_all", AsyncMock(return_value=None))
    db = FakeDb([FakeResult(scalar_one_or_none=None), FakeResult(scalars_list=[])])
    svc = PostMaintenanceRecoveryService(db)
    assert await svc.snapshot_health(1) is None


@pytest.mark.asyncio
async def test_snapshot_health_uses_latest_telemetry_reading(monkeypatch):
    monkeypatch.setattr("services.ml.recovery.is_ml_service_available", AsyncMock(return_value=True))
    predict_mock = AsyncMock(return_value={"unified_health_score": 90.0})
    monkeypatch.setattr("services.ml.recovery.ml_client.predict_all", predict_mock)
    latest = SimpleNamespace(
        air_temperature=295.0, process_temperature=305.0, rotational_speed=1400,
        torque=35.0, tool_wear=12.0, recorded_at=datetime.now(timezone.utc),
    )
    db = FakeDb([FakeResult(scalar_one_or_none=latest), FakeResult(scalars_list=[latest])])
    svc = PostMaintenanceRecoveryService(db)
    await svc.snapshot_health(1)
    _, kwargs = predict_mock.call_args
    assert kwargs["air_temperature"] == 295.0
    assert kwargs["tool_wear"] == 12


@pytest.mark.asyncio
async def test_snapshot_health_swallows_exceptions(monkeypatch):
    monkeypatch.setattr(
        "services.ml.recovery.is_ml_service_available", AsyncMock(side_effect=RuntimeError("boom"))
    )
    svc = PostMaintenanceRecoveryService(FakeDb())
    assert await svc.snapshot_health(1) is None
