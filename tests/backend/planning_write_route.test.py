"""Unit tests for the route-level handlers in
app/backend/modules/shared/routes/planning/write.py: create_planning,
resend_planning_emails, delete_planning, submit/approve/reject_planning.
The pure helpers (_resolve_planning_statut, _collect_user_ids,
_add_machines_to_planning, _validate_shift_compatibility) are already
covered in planning_write_update.test.py."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from models.alertes import Alert  # noqa: F401 — registers Alert mapper (needed by Utilisateurs relationship)
import modules.shared.routes.planning.write as write_mod
from modules.shared.routes.planning.write import (
    PlanningCreateData,
    approve_planning,
    create_planning,
    delete_planning,
    reject_planning,
    resend_planning_emails,
    submit_planning,
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
        self.added = []
        self.committed = 0
        self.rolled_back = 0

    async def execute(self, *_a, **_k):
        return self._results.pop(0)

    def add(self, obj):
        self.added.append(obj)
        if getattr(obj, "id", None) is None:
            obj.id = 42

    async def commit(self):
        self.committed += 1

    async def refresh(self, obj):
        pass

    async def rollback(self):
        self.rolled_back += 1


def _user():
    return SimpleNamespace(id=1, nom="Alice")


def _data(**overrides):
    base = dict(
        identifiant_planning="P-1",
        date_debut=datetime(2026, 1, 1, tzinfo=timezone.utc),
        date_fin=datetime(2026, 1, 2, tzinfo=timezone.utc),
        type="REGULAR",
    )
    base.update(overrides)
    return PlanningCreateData(**base)


@pytest.fixture(autouse=True)
def _stub_collaborators(monkeypatch):
    monkeypatch.setattr(write_mod, "verify_admin", lambda user: None)
    monkeypatch.setattr(write_mod, "verify_cheftech", lambda user: None)
    monkeypatch.setattr(write_mod, "AuditService", lambda db: SimpleNamespace(
        log_create=AsyncMock(), log_update=AsyncMock(), log_delete=AsyncMock(),
    ))


# ── create_planning ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_planning_success_no_users_no_machines(monkeypatch):
    monkeypatch.setattr(
        write_mod, "PlanningsService",
        lambda db: SimpleNamespace(get_by_id=AsyncMock(return_value=SimpleNamespace(id=42))),
    )
    monkeypatch.setattr(
        write_mod, "get_planning_with_users",
        AsyncMock(return_value={"id": 42, "identifiant_planning": "P-1"}),
    )
    db = FakeDb()
    result = await create_planning(data=_data(), current_user=_user(), db=db)
    assert result["id"] == 42
    assert db.committed >= 1


@pytest.mark.asyncio
async def test_create_planning_with_machines_and_users(monkeypatch):
    monkeypatch.setattr(
        write_mod, "PlanningsService",
        lambda db: SimpleNamespace(get_by_id=AsyncMock(return_value=SimpleNamespace(id=42))),
    )
    monkeypatch.setattr(
        write_mod, "get_planning_with_users",
        AsyncMock(return_value={"id": 42, "assigned_users": [1], "machine_ids": [5]}),
    )
    monkeypatch.setattr(write_mod, "send_planning_notifications", AsyncMock())
    monkeypatch.setattr(write_mod.send_planning_assignment_emails, "delay", lambda *a: None)
    user_with_email = SimpleNamespace(id=1, nom="Bob", email="bob@x.com")
    db = FakeDb([
        FakeResult(scalars_list=[]),  # _validate_shift_compatibility only runs for SHIFT type, skipped here
    ])
    # machine_ids present -> _add_machines_to_planning runs for real (commits), no db.execute needed
    # user notifications -> db.execute for users_result
    db._results.append(FakeResult(scalars_list=[user_with_email]))
    result = await create_planning(
        data=_data(machine_ids=[5, 5], chef_operation_id=1), current_user=_user(), db=db,
    )
    assert result["id"] == 42


@pytest.mark.asyncio
async def test_create_planning_unexpected_exception_rolls_back(monkeypatch):
    class _FailingDb(FakeDb):
        async def commit(self):
            raise RuntimeError("db down")

    db = _FailingDb()
    with pytest.raises(HTTPException) as exc_info:
        await create_planning(data=_data(), current_user=_user(), db=db)
    assert exc_info.value.status_code == 500
    assert db.rolled_back == 1


# ── resend_planning_emails ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resend_emails_planning_not_found(monkeypatch):
    monkeypatch.setattr(
        write_mod, "PlanningsService",
        lambda db: SimpleNamespace(get_by_id=AsyncMock(return_value=None)),
    )
    with pytest.raises(HTTPException) as exc_info:
        await resend_planning_emails(planning_id=99, current_user=_user(), db=FakeDb())
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_resend_emails_no_assigned_users_returns_zero(monkeypatch):
    planning = SimpleNamespace(id=1)
    monkeypatch.setattr(
        write_mod, "PlanningsService",
        lambda db: SimpleNamespace(get_by_id=AsyncMock(return_value=planning)),
    )
    db = FakeDb([FakeResult(rows=[])])
    result = await resend_planning_emails(planning_id=1, current_user=_user(), db=db)
    assert result == {"queued": 0}


@pytest.mark.asyncio
async def test_resend_emails_no_recipients_with_email_returns_zero(monkeypatch):
    planning = SimpleNamespace(id=1)
    monkeypatch.setattr(
        write_mod, "PlanningsService",
        lambda db: SimpleNamespace(get_by_id=AsyncMock(return_value=planning)),
    )
    user_no_email = SimpleNamespace(id=1, nom="Bob", email=None)
    db = FakeDb([FakeResult(rows=[(1,)]), FakeResult(scalars_list=[user_no_email])])
    result = await resend_planning_emails(planning_id=1, current_user=_user(), db=db)
    assert result == {"queued": 0}


@pytest.mark.asyncio
async def test_resend_emails_success(monkeypatch):
    planning = SimpleNamespace(
        id=1, identifiant_planning="P-1", date_debut=None, date_fin=None,
        type=None, shift_type=None, zone_travail=None,
    )
    monkeypatch.setattr(
        write_mod, "PlanningsService",
        lambda db: SimpleNamespace(get_by_id=AsyncMock(return_value=planning)),
    )
    user_with_email = SimpleNamespace(id=1, nom="Bob", email="bob@x.com")
    db = FakeDb([FakeResult(rows=[(1,)]), FakeResult(scalars_list=[user_with_email])])
    delay_calls = []
    monkeypatch.setattr(write_mod.send_planning_assignment_emails, "delay", lambda *a: delay_calls.append(a))
    result = await resend_planning_emails(planning_id=1, current_user=_user(), db=db)
    assert result == {"queued": 1}
    assert len(delay_calls) == 1


# ── delete_planning ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_planning_success(monkeypatch):
    monkeypatch.setattr(
        write_mod, "PlanningUtilisateursService",
        lambda db: SimpleNamespace(delete=AsyncMock()),
    )
    monkeypatch.setattr(
        write_mod, "PlanningsService",
        lambda db: SimpleNamespace(delete=AsyncMock(return_value=True)),
    )
    assignment = SimpleNamespace(id=1)
    db = FakeDb([FakeResult(scalars_list=[assignment])])
    result = await delete_planning(planning_id=1, current_user=_user(), db=db)
    assert result == {"message": "Planning deleted successfully", "id": 1}


@pytest.mark.asyncio
async def test_delete_planning_not_found(monkeypatch):
    monkeypatch.setattr(
        write_mod, "PlanningUtilisateursService",
        lambda db: SimpleNamespace(delete=AsyncMock()),
    )
    monkeypatch.setattr(
        write_mod, "PlanningsService",
        lambda db: SimpleNamespace(delete=AsyncMock(return_value=False)),
    )
    db = FakeDb([FakeResult(scalars_list=[])])
    with pytest.raises(HTTPException) as exc_info:
        await delete_planning(planning_id=99, current_user=_user(), db=db)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_planning_unexpected_exception_rolls_back(monkeypatch):
    class _RaisingDb(FakeDb):
        async def execute(self, *_a, **_k):
            raise RuntimeError("db down")

    db = _RaisingDb()
    with pytest.raises(HTTPException) as exc_info:
        await delete_planning(planning_id=1, current_user=_user(), db=db)
    assert exc_info.value.status_code == 500
    assert db.rolled_back == 1


# ── submit / approve / reject planning ────────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_planning_success(monkeypatch):
    planning = SimpleNamespace(id=1, planning_statut=None, identifiant_planning="P-1")
    monkeypatch.setattr(
        write_mod, "PlanningsService",
        lambda db: SimpleNamespace(get_by_id=AsyncMock(return_value=planning), update=AsyncMock()),
    )
    result = await submit_planning(planning_id=1, current_user=_user(), db=FakeDb())
    assert result["planning_statut"] == "SUBMITTED"


@pytest.mark.asyncio
async def test_submit_planning_not_found(monkeypatch):
    monkeypatch.setattr(
        write_mod, "PlanningsService",
        lambda db: SimpleNamespace(get_by_id=AsyncMock(return_value=None)),
    )
    with pytest.raises(HTTPException) as exc_info:
        await submit_planning(planning_id=99, current_user=_user(), db=FakeDb())
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_approve_planning_success(monkeypatch):
    planning = SimpleNamespace(id=1, planning_statut=None, identifiant_planning="P-1")
    monkeypatch.setattr(
        write_mod, "PlanningsService",
        lambda db: SimpleNamespace(get_by_id=AsyncMock(return_value=planning), update=AsyncMock()),
    )
    result = await approve_planning(planning_id=1, current_user=_user(), db=FakeDb())
    assert result["planning_statut"] == "APPROVED"


@pytest.mark.asyncio
async def test_approve_planning_not_found(monkeypatch):
    monkeypatch.setattr(
        write_mod, "PlanningsService",
        lambda db: SimpleNamespace(get_by_id=AsyncMock(return_value=None)),
    )
    with pytest.raises(HTTPException) as exc_info:
        await approve_planning(planning_id=99, current_user=_user(), db=FakeDb())
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_reject_planning_success(monkeypatch):
    planning = SimpleNamespace(id=1, planning_statut=None, identifiant_planning="P-1")
    monkeypatch.setattr(
        write_mod, "PlanningsService",
        lambda db: SimpleNamespace(get_by_id=AsyncMock(return_value=planning), update=AsyncMock()),
    )
    result = await reject_planning(planning_id=1, current_user=_user(), db=FakeDb())
    assert result["planning_statut"] == "REJECTED"


@pytest.mark.asyncio
async def test_reject_planning_not_found(monkeypatch):
    monkeypatch.setattr(
        write_mod, "PlanningsService",
        lambda db: SimpleNamespace(get_by_id=AsyncMock(return_value=None)),
    )
    with pytest.raises(HTTPException) as exc_info:
        await reject_planning(planning_id=99, current_user=_user(), db=FakeDb())
    assert exc_info.value.status_code == 404
