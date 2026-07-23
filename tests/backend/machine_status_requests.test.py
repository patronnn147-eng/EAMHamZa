"""Unit tests for app/backend/modules/shared/services/machine_status_requests.py."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from models.alertes import Alert  # noqa: F401 — registers Alert mapper (needed by Utilisateurs relationship)
from models.machine_status_change_request import RequestStatus
from modules.shared.services.machine_status_requests import (
    approve_status_change_request,
    create_status_change_request,
    list_pending_requests,
    reject_status_change_request,
)


class FakeScalarsResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class FakeDb:
    """Supports the .scalar()/.execute()/.add()/.flush()/.commit() surface this
    service uses. `scalars` feeds db.scalar() calls in FIFO order; `execute_results`
    feeds db.execute() calls in FIFO order."""

    def __init__(self, scalars=None, execute_results=None):
        self._scalars = list(scalars or [])
        self._execute_results = list(execute_results or [])
        self.added = []
        self.committed = 0
        self.flushed = 0

    async def scalar(self, *_a, **_k):
        return self._scalars.pop(0)

    async def execute(self, *_a, **_k):
        return self._execute_results.pop(0)

    def add(self, obj):
        self.added.append(obj)
        if getattr(obj, "id", None) is None:
            obj.id = 999

    async def flush(self):
        self.flushed += 1

    async def commit(self):
        self.committed += 1


def _machine(mid=1, statut="OPERATIONNELLE", nom="M1"):
    return SimpleNamespace(id=mid, statut=statut, nom=nom)


def _request(rid=1, machine_id=1, status=RequestStatus.PENDING, from_status="OPERATIONNELLE",
             to_status="EN_PANNE"):
    return SimpleNamespace(
        id=rid, machine_id=machine_id, status=status, from_status=from_status,
        to_status=to_status, reviewed_by=None, reviewed_at=None, review_note=None,
        requested_by=None, requested_at=None, source_intervention_id=None,
    )


# ── create_status_change_request ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_status_change_request_machine_not_found_returns_none():
    db = FakeDb(scalars=[None])
    result = await create_status_change_request(1, "EN_PANNE", requested_by=1, source_intervention_id=None, db=db)
    assert result is None


@pytest.mark.asyncio
async def test_create_status_change_request_same_status_returns_none():
    machine = _machine(statut="EN_PANNE")
    db = FakeDb(scalars=[machine])
    result = await create_status_change_request(1, "EN_PANNE", requested_by=1, source_intervention_id=None, db=db)
    assert result is None


@pytest.mark.asyncio
async def test_create_status_change_request_supersedes_existing_pending(monkeypatch):
    machine = _machine(statut="OPERATIONNELLE")
    existing_pending = _request(rid=5, status=RequestStatus.PENDING)
    db = FakeDb(
        scalars=[machine],
        execute_results=[FakeScalarsResult([existing_pending])],
    )
    result = await create_status_change_request(1, "EN_PANNE", requested_by=2, source_intervention_id=None, db=db)
    assert existing_pending.status == RequestStatus.REJECTED
    assert existing_pending.review_note == "Superseded by newer request"
    assert result == 999  # FakeDb.add() assigns id 999
    assert db.flushed == 1


# ── approve_status_change_request ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_approve_request_not_found():
    db = FakeDb(scalars=[None])
    result = await approve_status_change_request(1, approved_by=1, db=db)
    assert result == {"success": False, "error": "Request not found"}


@pytest.mark.asyncio
async def test_approve_request_not_pending():
    request = _request(status=RequestStatus.APPROVED)
    db = FakeDb(scalars=[request])
    result = await approve_status_change_request(1, approved_by=1, db=db)
    assert result["success"] is False
    assert "not pending" in result["error"]


@pytest.mark.asyncio
async def test_approve_request_machine_not_found():
    request = _request()
    db = FakeDb(scalars=[request, None])
    result = await approve_status_change_request(1, approved_by=1, db=db)
    assert result == {"success": False, "error": "Machine not found"}


@pytest.mark.asyncio
async def test_approve_request_success_updates_machine_statut(monkeypatch):
    request = _request(to_status="EN_PANNE")
    machine = _machine(statut="OPERATIONNELLE")
    db = FakeDb(scalars=[request, machine])
    monkeypatch.setattr(
        "services.audit.AuditService",
        lambda db: SimpleNamespace(log_update=AsyncMock()),
    )
    result = await approve_status_change_request(1, approved_by=2, db=db)
    assert result["success"] is True
    assert result["statut"] == "EN_PANNE"
    assert machine.statut == "EN_PANNE"
    assert request.status == RequestStatus.APPROVED
    assert db.committed == 1


@pytest.mark.asyncio
async def test_approve_request_audit_failure_does_not_block_approval(monkeypatch):
    request = _request(to_status="EN_PANNE")
    machine = _machine(statut="OPERATIONNELLE")
    db = FakeDb(scalars=[request, machine])
    monkeypatch.setattr(
        "services.audit.AuditService",
        lambda db: SimpleNamespace(log_update=AsyncMock(side_effect=RuntimeError("boom"))),
    )
    result = await approve_status_change_request(1, approved_by=2, db=db)
    assert result["success"] is True
    assert db.committed == 1


# ── reject_status_change_request ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reject_request_not_found():
    db = FakeDb(scalars=[None])
    result = await reject_status_change_request(1, rejected_by=1, note="no", db=db)
    assert result == {"success": False, "error": "Request not found"}


@pytest.mark.asyncio
async def test_reject_request_not_pending():
    request = _request(status=RequestStatus.REJECTED)
    db = FakeDb(scalars=[request])
    result = await reject_status_change_request(1, rejected_by=1, note="no", db=db)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_reject_request_success_leaves_machine_statut_untouched(monkeypatch):
    request = _request(to_status="EN_PANNE")
    machine = _machine(statut="OPERATIONNELLE")
    db = FakeDb(scalars=[request, machine])
    monkeypatch.setattr(
        "services.audit.AuditService",
        lambda db: SimpleNamespace(log_update=AsyncMock()),
    )
    result = await reject_status_change_request(1, rejected_by=2, note="not needed", db=db)
    assert result == {"success": True, "request_id": 1, "status": "REJECTED"}
    assert machine.statut == "OPERATIONNELLE"  # untouched
    assert request.status == RequestStatus.REJECTED
    assert request.review_note == "not needed"


@pytest.mark.asyncio
async def test_reject_request_machine_missing_still_succeeds(monkeypatch):
    request = _request()
    db = FakeDb(scalars=[request, None])
    monkeypatch.setattr(
        "services.audit.AuditService",
        lambda db: SimpleNamespace(log_update=AsyncMock()),
    )
    result = await reject_status_change_request(1, rejected_by=2, note=None, db=db)
    assert result["success"] is True


# ── list_pending_requests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_pending_requests_maps_joined_rows():
    from datetime import datetime, timezone

    request = _request()
    request.requested_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    machine = _machine(nom="Machine A")
    user = SimpleNamespace(nom="Tech Bob")

    class FakeRowsResult:
        def all(self):
            return [(request, machine, user)]

    db = FakeDb(execute_results=[FakeRowsResult()])
    result = await list_pending_requests(db)
    assert len(result) == 1
    assert result[0]["machine_name"] == "Machine A"
    assert result[0]["requested_by_name"] == "Tech Bob"
    assert result[0]["requested_at"] == "2026-01-01T00:00:00+00:00"


@pytest.mark.asyncio
async def test_list_pending_requests_handles_no_requester():
    request = _request()
    machine = _machine()

    class FakeRowsResult:
        def all(self):
            return [(request, machine, None)]

    db = FakeDb(execute_results=[FakeRowsResult()])
    result = await list_pending_requests(db)
    assert result[0]["requested_by_name"] is None
