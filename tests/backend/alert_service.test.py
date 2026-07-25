"""Unit tests for app/backend/services/alertes.py (AlertService)."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from models.alertes import Alert, AlertConfig, AlertSeverity, AlertType
import services.alertes as alertes_mod
from services.alertes import AlertService


class FakeResult:
    def __init__(self, scalar_one_or_none=None, scalar_value=None, scalars_list=None, rows=None):
        self._soo = scalar_one_or_none
        self._scalar_value = scalar_value
        self._scalars_list = scalars_list
        self._rows = rows

    def scalar_one_or_none(self):
        return self._soo

    def scalar(self):
        return self._scalar_value

    def scalars(self):
        return self

    def all(self):
        return self._rows if self._rows is not None else (self._scalars_list or [])


class FakeDb:
    def __init__(self, execute_results=None):
        self._results = list(execute_results or [])
        self.added = []
        self.committed = 0
        self.rolled_back = 0
        self.refreshed = 0

    async def execute(self, *_a, **_k):
        return self._results.pop(0)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed += 1

    async def rollback(self):
        self.rolled_back += 1

    async def refresh(self, obj):
        self.refreshed += 1


@pytest.fixture(autouse=True)
def _stub_notification_side_effects(monkeypatch):
    """create_alert always calls _send_alert_notification -> NotificationsService +
    broadcaster; stub both so create_alert tests stay focused on alert creation."""
    monkeypatch.setattr(
        "services.notifications.NotificationsService",
        lambda db: SimpleNamespace(create=AsyncMock(), send_workflow_notification=AsyncMock()),
    )
    monkeypatch.setattr(alertes_mod.broadcaster, "broadcast", AsyncMock())


# ── create_alert ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_alert_returns_existing_when_active_duplicate_exists():
    existing = SimpleNamespace(id=1)
    db = FakeDb([FakeResult(scalar_one_or_none=existing)])
    svc = AlertService(db)
    result = await svc.create_alert(1, AlertType.RUL_WARNING, AlertSeverity.HIGH, "msg")
    assert result is existing
    assert db.committed == 0  # no new alert created


@pytest.mark.asyncio
async def test_create_alert_creates_new_and_notifies():
    machine = SimpleNamespace(nom="Press-1")
    db = FakeDb([
        FakeResult(scalar_one_or_none=None),  # no existing active alert
        FakeResult(scalar_one_or_none=machine),  # machine lookup for notification
    ])
    svc = AlertService(db)
    result = await svc.create_alert(1, AlertType.RUL_WARNING, AlertSeverity.HIGH, "msg", rul_days=5.0)
    assert db.committed == 1
    assert len(db.added) == 1


@pytest.mark.asyncio
async def test_create_alert_rolls_back_on_exception():
    class _FailingDb(FakeDb):
        async def execute(self, *_a, **_k):
            raise RuntimeError("db down")

    svc = AlertService(_FailingDb())
    with pytest.raises(RuntimeError):
        await svc.create_alert(1, AlertType.RUL_WARNING, AlertSeverity.HIGH, "msg")


@pytest.mark.asyncio
async def test_send_alert_notification_swallows_failure(monkeypatch):
    monkeypatch.setattr(
        "services.notifications.NotificationsService",
        lambda db: SimpleNamespace(create=AsyncMock(side_effect=RuntimeError("notif down"))),
    )
    alert = SimpleNamespace(
        id=1, severity=AlertSeverity.HIGH, alert_type=AlertType.RUL_WARNING, message="msg",
    )
    svc = AlertService(FakeDb())
    await svc._send_alert_notification(alert, "Press-1")  # must not raise


# ── get_active_alerts ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_active_alerts_returns_list():
    alerts = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    db = FakeDb([FakeResult(scalars_list=alerts)])
    svc = AlertService(db)
    result = await svc.get_active_alerts()
    assert result == alerts


@pytest.mark.asyncio
async def test_get_active_alerts_filters_by_machine_and_severity():
    db = FakeDb([FakeResult(scalars_list=[])])
    svc = AlertService(db)
    result = await svc.get_active_alerts(machine_id=5, severity=AlertSeverity.CRITICAL)
    assert result == []


# ── dismiss_alert ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dismiss_alert_success():
    alert = SimpleNamespace(id=1, is_active=True, dismissed_at=None, dismissed_by=None)
    db = FakeDb([FakeResult(scalar_one_or_none=alert)])
    svc = AlertService(db)
    result = await svc.dismiss_alert(1, user_id=7)
    assert result.is_active is False
    assert result.dismissed_by == 7


@pytest.mark.asyncio
async def test_dismiss_alert_not_found_returns_none():
    db = FakeDb([FakeResult(scalar_one_or_none=None)])
    svc = AlertService(db)
    assert await svc.dismiss_alert(99, user_id=7) is None


# ── get_alert_stats ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_alert_stats_aggregates_counts():
    results = [FakeResult(scalar_value=10)]  # total_active
    for _ in AlertSeverity:
        results.append(FakeResult(scalar_value=1))
    results.append(FakeResult(scalar_value=3))  # machines_affected
    db = FakeDb(results)
    svc = AlertService(db)
    stats = await svc.get_alert_stats()
    assert stats["total_active"] == 10
    assert stats["machines_affected"] == 3
    assert len(stats["by_severity"]) == len(AlertSeverity)


# ── get_config / update_config ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_config_returns_existing():
    config = SimpleNamespace(id=1)
    db = FakeDb([FakeResult(scalar_one_or_none=config)])
    svc = AlertService(db)
    assert await svc.get_config() is config


@pytest.mark.asyncio
async def test_get_config_creates_default_when_missing():
    db = FakeDb([FakeResult(scalar_one_or_none=None)])
    svc = AlertService(db)
    config = await svc.get_config()
    assert config is not None
    assert db.committed == 1


@pytest.mark.asyncio
async def test_update_config_applies_known_fields_only():
    config = SimpleNamespace(id=1, rul_threshold_days=5)
    db = FakeDb([FakeResult(scalar_one_or_none=config)])
    svc = AlertService(db)
    updated = await svc.update_config({"rul_threshold_days": 10, "not_a_field": "x"})
    assert updated.rul_threshold_days == 10
    assert not hasattr(updated, "not_a_field")


# ── _get_rul_severity ────────────────────────────────────────────────────────

@pytest.mark.parametrize("rul_days,expected", [
    (0.5, AlertSeverity.CRITICAL),
    (2.0, AlertSeverity.HIGH),
    (5.0, AlertSeverity.MEDIUM),
    (30.0, AlertSeverity.LOW),
])
def test_get_rul_severity_thresholds(rul_days, expected):
    svc = AlertService(FakeDb())
    assert svc._get_rul_severity(rul_days) == expected


# ── _get_machine_inputs ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_machine_inputs_no_telemetry_uses_defaults():
    db = FakeDb([FakeResult(scalars_list=[]), FakeResult(scalars_list=[])])
    svc = AlertService(db)
    interventions, telemetry, air, proc, rpm, torq, wear = await svc._get_machine_inputs(1)
    assert telemetry == []
    assert air == 300.0 and wear == 0


@pytest.mark.asyncio
async def test_get_machine_inputs_uses_latest_reading():
    latest = SimpleNamespace(
        air_temperature=295.0, process_temperature=305.0, rotational_speed=1400,
        torque=35.0, tool_wear=12,
    )
    db = FakeDb([FakeResult(scalars_list=[]), FakeResult(scalars_list=[latest])])
    svc = AlertService(db)
    _, telemetry, air, proc, rpm, torq, wear = await svc._get_machine_inputs(1)
    assert air == 295.0
    assert wear == 12


# ── link_existing_work_order ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_link_existing_work_order_success():
    alert = SimpleNamespace(id=1, is_linked_to_wo=False, work_order_id=None)
    wo = SimpleNamespace(id=10)
    db = FakeDb([FakeResult(scalar_one_or_none=alert), FakeResult(scalar_one_or_none=wo)])
    svc = AlertService(db)
    result = await svc.link_existing_work_order(1, 10)
    assert result.is_linked_to_wo is True
    assert result.work_order_id == 10


@pytest.mark.asyncio
async def test_link_existing_work_order_alert_not_found():
    db = FakeDb([FakeResult(scalar_one_or_none=None)])
    svc = AlertService(db)
    assert await svc.link_existing_work_order(99, 10) is None


@pytest.mark.asyncio
async def test_link_existing_work_order_wo_not_found():
    alert = SimpleNamespace(id=1)
    db = FakeDb([FakeResult(scalar_one_or_none=alert), FakeResult(scalar_one_or_none=None)])
    svc = AlertService(db)
    assert await svc.link_existing_work_order(1, 999) is None


# ── send_alert_email ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_alert_email_no_notification_email_returns_false():
    config = SimpleNamespace(notification_email=None)
    alert = SimpleNamespace(severity=AlertSeverity.CRITICAL)
    svc = AlertService(FakeDb())
    assert await svc.send_alert_email(alert, config) is False


@pytest.mark.asyncio
async def test_send_alert_email_low_severity_digest_skipped():
    config = SimpleNamespace(notification_email="a@x.com", frequency="daily")
    alert = SimpleNamespace(severity=AlertSeverity.LOW)
    svc = AlertService(FakeDb())
    assert await svc.send_alert_email(alert, config) is False


@pytest.mark.asyncio
async def test_send_alert_email_sends_to_recipients(monkeypatch):
    config = SimpleNamespace(notification_email="a@x.com", frequency="immediate")
    alert = SimpleNamespace(
        id=1, severity=AlertSeverity.CRITICAL, alert_type=AlertType.RUL_WARNING,
        message="msg", machine=None, machine_id=5, rul_days=3.0, failure_probability=None,
    )
    db = FakeDb([FakeResult(rows=[("ops@x.com",)])])
    svc = AlertService(db)

    fake_email_service = SimpleNamespace(send_email=lambda *a, **k: None)
    monkeypatch.setattr("core.email.EmailService", lambda: fake_email_service)

    result = await svc.send_alert_email(alert, config)
    assert result is True


@pytest.mark.asyncio
async def test_send_alert_email_swallows_failure(monkeypatch):
    config = SimpleNamespace(notification_email="a@x.com", frequency="immediate")
    alert = SimpleNamespace(severity=AlertSeverity.CRITICAL, machine=None, machine_id=5)

    class _RaisingDb(FakeDb):
        async def execute(self, *_a, **_k):
            raise RuntimeError("db down")

    svc = AlertService(_RaisingDb())
    result = await svc.send_alert_email(alert, config)
    assert result is False


# ── _process_machine_alerts ──────────────────────────────────────────────────

def _alert_config(**overrides):
    base = dict(
        enable_rul_alerts=True, rul_threshold_days=7.0,
        enable_failure_alerts=True, failure_probability_threshold=0.7,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_process_machine_alerts_emits_rul_warning(monkeypatch):
    machine = SimpleNamespace(id=1, nom="M1")
    monkeypatch.setattr(
        "modules.ml.rul_calculator.RULCalculator.calculate_rul",
        lambda *a, **k: {"rul_days": 2.0, "failure_probability": 10},
    )
    db = FakeDb([
        FakeResult(scalars_list=[]),  # interventions
        FakeResult(scalars_list=[]),  # telemetry
        FakeResult(scalar_one_or_none=None),  # create_alert: no existing duplicate
        FakeResult(scalar_one_or_none=machine),  # create_alert: machine lookup for notification
    ])
    svc = AlertService(db)
    counts = await svc._process_machine_alerts(machine, _alert_config(), _ml_available=False)
    assert counts == {"rul_warnings": 1, "failure_predicted": 0}


@pytest.mark.asyncio
async def test_process_machine_alerts_emits_failure_predicted(monkeypatch):
    machine = SimpleNamespace(id=1, nom="M1")
    monkeypatch.setattr(
        "modules.ml.rul_calculator.RULCalculator.calculate_rul",
        lambda *a, **k: {"rul_days": 100.0, "failure_probability": 90},
    )
    db = FakeDb([
        FakeResult(scalars_list=[]),
        FakeResult(scalars_list=[]),
        FakeResult(scalar_one_or_none=None),
        FakeResult(scalar_one_or_none=machine),
    ])
    svc = AlertService(db)
    counts = await svc._process_machine_alerts(machine, _alert_config(), _ml_available=False)
    assert counts == {"rul_warnings": 0, "failure_predicted": 1}


@pytest.mark.asyncio
async def test_process_machine_alerts_no_alerts_when_disabled(monkeypatch):
    machine = SimpleNamespace(id=1, nom="M1")
    monkeypatch.setattr(
        "modules.ml.rul_calculator.RULCalculator.calculate_rul",
        lambda *a, **k: {"rul_days": 0.5, "failure_probability": 99},
    )
    db = FakeDb([FakeResult(scalars_list=[]), FakeResult(scalars_list=[])])
    svc = AlertService(db)
    counts = await svc._process_machine_alerts(
        machine, _alert_config(enable_rul_alerts=False, enable_failure_alerts=False), _ml_available=False
    )
    assert counts == {"rul_warnings": 0, "failure_predicted": 0}


@pytest.mark.asyncio
async def test_process_machine_alerts_calls_ml_client_when_available(monkeypatch):
    machine = SimpleNamespace(id=1, nom="M1")
    predict_mock = AsyncMock(return_value={"unified_health_score": 80.0})
    monkeypatch.setattr("core.ml_client.ml_client.predict_all", predict_mock)
    monkeypatch.setattr(
        "modules.ml.rul_calculator.RULCalculator.calculate_rul",
        lambda *a, **k: {"rul_days": 100.0, "failure_probability": 5},
    )
    latest = SimpleNamespace(
        air_temperature=295.0, process_temperature=305.0, rotational_speed=1400,
        torque=35.0, tool_wear=12,
    )
    db = FakeDb([FakeResult(scalars_list=[]), FakeResult(scalars_list=[latest])])
    svc = AlertService(db)
    counts = await svc._process_machine_alerts(machine, _alert_config(), _ml_available=True)
    predict_mock.assert_awaited_once()
    assert counts == {"rul_warnings": 0, "failure_predicted": 0}


@pytest.mark.asyncio
async def test_process_machine_alerts_swallows_ml_client_exception(monkeypatch):
    machine = SimpleNamespace(id=1, nom="M1")
    monkeypatch.setattr(
        "core.ml_client.ml_client.predict_all", AsyncMock(side_effect=RuntimeError("ml down"))
    )
    monkeypatch.setattr(
        "modules.ml.rul_calculator.RULCalculator.calculate_rul",
        lambda *a, **k: {"rul_days": 100.0, "failure_probability": 5},
    )
    db = FakeDb([FakeResult(scalars_list=[]), FakeResult(scalars_list=[])])
    svc = AlertService(db)
    counts = await svc._process_machine_alerts(machine, _alert_config(), _ml_available=True)
    assert counts == {"rul_warnings": 0, "failure_predicted": 0}


@pytest.mark.asyncio
async def test_process_machine_alerts_swallows_outer_exception():
    machine = SimpleNamespace(id=1, nom="M1")

    class _RaisingDb(FakeDb):
        async def execute(self, *_a, **_k):
            raise RuntimeError("db down")

    svc = AlertService(_RaisingDb())
    counts = await svc._process_machine_alerts(machine, _alert_config(), _ml_available=False)
    assert counts == {"rul_warnings": 0, "failure_predicted": 0}


# ── check_and_create_alerts ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_and_create_alerts_aggregates_per_machine_counts(monkeypatch):
    m1 = SimpleNamespace(id=1, nom="M1")
    m2 = SimpleNamespace(id=2, nom="M2")
    config = _alert_config()
    monkeypatch.setattr("core.ml_client.is_ml_service_available", AsyncMock(return_value=False))

    db = FakeDb([
        FakeResult(scalar_one_or_none=config),  # get_config
        FakeResult(scalars_list=[m1, m2]),  # machines
    ])
    svc = AlertService(db)

    call_counts = [{"rul_warnings": 1, "failure_predicted": 0}, {"rul_warnings": 0, "failure_predicted": 1}]
    svc._process_machine_alerts = AsyncMock(side_effect=call_counts)

    result = await svc.check_and_create_alerts()
    assert result == {"rul_warnings": 1, "failure_predicted": 1, "anomaly_detected": 0}
    assert svc._process_machine_alerts.await_count == 2


@pytest.mark.asyncio
async def test_check_and_create_alerts_reraises_on_error(monkeypatch):
    class _RaisingDb(FakeDb):
        async def execute(self, *_a, **_k):
            raise RuntimeError("db down")

    svc = AlertService(_RaisingDb())
    with pytest.raises(RuntimeError):
        await svc.check_and_create_alerts()
