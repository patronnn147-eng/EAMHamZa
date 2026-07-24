"""Unit tests for the route-level pieces of
app/backend/modules/shared/routes/planning/update.py not already covered
in planning_write_update.test.py: _send_planning_update_notifications,
_try_audit_update_planning, and the top-level update_planning route."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from datetime import datetime, timezone

from models.alertes import Alert  # noqa: F401 — registers Alert mapper (needed by Utilisateurs relationship)
import modules.shared.routes.planning.update as update_mod
from modules.shared.routes.planning.update import (
    PlanningUpdateData,
    _send_planning_update_notifications,
    _try_audit_update_planning,
    update_planning,
)


class FakeResult:
    def __init__(self, rows=None, scalars_list=None):
        self._rows = rows or []
        self._scalars_list = scalars_list

    def fetchall(self):
        return self._rows

    def scalars(self):
        return self

    def all(self):
        return self._scalars_list if self._scalars_list is not None else self._rows


class FakeDb:
    def __init__(self, execute_results=None):
        self._results = list(execute_results or [])
        self.rolled_back = 0

    async def execute(self, *_a, **_k):
        return self._results.pop(0)

    async def rollback(self):
        self.rolled_back += 1


def _admin_user():
    return SimpleNamespace(id=1, nom="Alice")


# ── _send_planning_update_notifications ─────────────────────────────────────

@pytest.mark.asyncio
async def test_send_notifications_noop_without_users():
    db = FakeDb()
    await _send_planning_update_notifications(db, 1, "P-1", [], {})  # no execute call needed


@pytest.mark.asyncio
async def test_send_notifications_sends_emails_to_recipients_with_email(monkeypatch):
    monkeypatch.setattr(update_mod, "send_planning_notifications", AsyncMock())
    delay_mock = SimpleNamespace(called=False, args=None)

    def _fake_delay(*args):
        delay_mock.called = True
        delay_mock.args = args

    monkeypatch.setattr(update_mod.send_planning_assignment_emails, "delay", _fake_delay)

    user_with_email = SimpleNamespace(id=1, nom="Bob", email="bob@x.com")
    user_without_email = SimpleNamespace(id=2, nom="Carl", email=None)
    db = FakeDb([FakeResult(scalars_list=[user_with_email, user_without_email])])

    await _send_planning_update_notifications(db, 1, "P-1", [1, 2], {"id": 1})

    update_mod.send_planning_notifications.assert_awaited_once()
    assert delay_mock.called is True
    recipients = delay_mock.args[0]
    assert len(recipients) == 1
    assert recipients[0]["email"] == "bob@x.com"


@pytest.mark.asyncio
async def test_send_notifications_skips_email_dispatch_when_no_recipients_have_email(monkeypatch):
    monkeypatch.setattr(update_mod, "send_planning_notifications", AsyncMock())
    delay_calls = []
    monkeypatch.setattr(update_mod.send_planning_assignment_emails, "delay", lambda *a: delay_calls.append(a))

    user_without_email = SimpleNamespace(id=2, nom="Carl", email=None)
    db = FakeDb([FakeResult(scalars_list=[user_without_email])])

    await _send_planning_update_notifications(db, 1, "P-1", [2], {"id": 1})
    assert delay_calls == []


# ── _try_audit_update_planning ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_try_audit_update_planning_success(monkeypatch):
    log_mock = AsyncMock()
    monkeypatch.setattr(update_mod, "AuditService", lambda db: SimpleNamespace(log_update=log_mock))
    await _try_audit_update_planning(
        FakeDb(), 1, "OLD-ID", "2026-01-01", "2026-01-02", "REGULAR", "DAY",
        {"identifiant_planning": "NEW-ID"}, 1, "Alice", "NEW-ID",
    )
    log_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_try_audit_update_planning_swallows_failure(monkeypatch):
    monkeypatch.setattr(
        update_mod, "AuditService",
        lambda db: SimpleNamespace(log_update=AsyncMock(side_effect=RuntimeError("boom"))),
    )
    await _try_audit_update_planning(
        FakeDb(), 1, "OLD-ID", None, None, None, None, {}, 1, "Alice", "OLD-ID",
    )  # must not raise


# ── update_planning (top-level route) ────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_planning_not_found(monkeypatch):
    monkeypatch.setattr(update_mod, "verify_admin", lambda user: None)
    monkeypatch.setattr(
        update_mod, "PlanningsService",
        lambda db: SimpleNamespace(get_by_id=AsyncMock(return_value=None)),
    )
    with pytest.raises(HTTPException) as exc_info:
        await update_planning(
            planning_id=99, data=PlanningUpdateData(), current_user=_admin_user(), db=FakeDb(),
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_planning_success(monkeypatch):
    monkeypatch.setattr(update_mod, "verify_admin", lambda user: None)
    planning = SimpleNamespace(
        identifiant_planning="OLD-ID", date_debut=None, date_fin=None, type=None,
        shift_type=None, chef_operation_id=None, chef_technique_id=None,
        zone_travail=None, created_at=None,
    )
    monkeypatch.setattr(
        update_mod, "PlanningsService",
        lambda db: SimpleNamespace(
            get_by_id=AsyncMock(return_value=planning),
            update=AsyncMock(),
        ),
    )
    monkeypatch.setattr(update_mod, "_update_machine_assignments", AsyncMock(return_value=[1, 2]))
    monkeypatch.setattr(update_mod, "_rebuild_user_assignments", AsyncMock(return_value=[3, 4]))
    monkeypatch.setattr(update_mod, "_send_planning_update_notifications", AsyncMock())
    monkeypatch.setattr(update_mod, "_try_audit_update_planning", AsyncMock())
    monkeypatch.setattr(
        update_mod, "get_planning_with_users",
        AsyncMock(return_value={
            "id": 1, "identifiant_planning": "NEW-ID",
            "date_debut": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "date_fin": datetime(2026, 1, 2, tzinfo=timezone.utc),
            "type": "REGULAR", "shift_type": None, "chef_operation_id": None,
            "chef_technique_id": None, "zone_travail": None, "created_at": None,
            "assigned_users": [], "machine_ids": [1, 2],
        }),
    )
    db = FakeDb([FakeResult(rows=[])])  # existing_machines query

    result = await update_planning(
        planning_id=1, data=PlanningUpdateData(identifiant_planning="NEW-ID"),
        current_user=_admin_user(), db=db,
    )
    assert result.identifiant_planning == "NEW-ID"


@pytest.mark.asyncio
async def test_update_planning_unexpected_exception_rolls_back(monkeypatch):
    monkeypatch.setattr(update_mod, "verify_admin", lambda user: None)

    async def _raise(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        update_mod, "PlanningsService",
        lambda db: SimpleNamespace(get_by_id=_raise),
    )
    db = FakeDb()
    with pytest.raises(HTTPException) as exc_info:
        await update_planning(
            planning_id=1, data=PlanningUpdateData(), current_user=_admin_user(), db=db,
        )
    assert exc_info.value.status_code == 500
    assert db.rolled_back == 1
