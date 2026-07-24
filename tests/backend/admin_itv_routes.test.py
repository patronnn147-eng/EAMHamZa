"""Unit tests for app/backend/modules/admin/admin_itv.py."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from models.alertes import Alert  # noqa: F401 — registers Alert mapper (needed by Utilisateurs relationship)
from models.utilisateurs import UserRole
import modules.admin.admin_itv as itv_mod
from modules.admin.admin_itv import (
    ItvRequestValidation,
    _handle_itv_approved,
    _handle_itv_rejected,
    get_all_pending_requests,
    validate_itv_request,
)
from services.inventory import InsufficientStockError


class FakeResult:
    def __init__(self, scalar_one_or_none=None, scalar_value=None, rows=None):
        self._soo = scalar_one_or_none
        self._scalar_value = scalar_value
        self._rows = rows

    def scalar_one_or_none(self):
        return self._soo

    def scalar(self):
        return self._scalar_value

    def all(self):
        return self._rows or []


class FakeDb:
    def __init__(self, execute_results=None):
        self._results = list(execute_results or [])
        self.added = []
        self.committed = 0
        self.rolled_back = 0
        self.flushed = 0

    async def execute(self, *_a, **_k):
        return self._results.pop(0)

    def add(self, obj):
        self.added.append(obj)
        if getattr(obj, "id", None) is None:
            obj.id = 100

    async def commit(self):
        self.committed += 1

    async def rollback(self):
        self.rolled_back += 1

    async def flush(self):
        self.flushed += 1


def _admin_user():
    return SimpleNamespace(id=1, nom="Alice", role=UserRole.ADMIN)


def _non_admin_user():
    return SimpleNamespace(id=1, nom="Bob", role=UserRole.TECHNICIEN)


@pytest.fixture(autouse=True)
def _stub_recovery_and_rmq(monkeypatch):
    monkeypatch.setattr(
        itv_mod, "PostMaintenanceRecoveryService",
        lambda db: SimpleNamespace(snapshot_health=AsyncMock(return_value=None)),
    )
    monkeypatch.setattr(itv_mod, "get_rabbitmq", AsyncMock(return_value=SimpleNamespace(publish_work_order_event=AsyncMock())))


# ── get_all_pending_requests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_all_pending_requests_non_admin_rejected():
    with pytest.raises(HTTPException) as exc_info:
        await get_all_pending_requests(page=1, size=10, current_user=_non_admin_user(), db=FakeDb())
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_all_pending_requests_empty():
    db = FakeDb([FakeResult(scalar_value=0), FakeResult(rows=[])])
    result = await get_all_pending_requests(page=1, size=10, current_user=_admin_user(), db=db)
    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_get_all_pending_requests_maps_rows():
    itv = SimpleNamespace(
        id=1, machine_id=5, priority="HAUTE", problem_description="noisy",
        statut="PENDING_APPROVAL", requested_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    db = FakeDb([FakeResult(scalar_value=1), FakeResult(rows=[(itv, "Press-1", "Bob")])])
    result = await get_all_pending_requests(page=1, size=10, current_user=_admin_user(), db=db)
    assert result.total == 1
    assert result.items[0].machine_nom == "Press-1"
    assert result.items[0].requested_by_nom == "Bob"


@pytest.mark.asyncio
async def test_get_all_pending_requests_exception_raises_500():
    class _RaisingDb(FakeDb):
        async def execute(self, *_a, **_k):
            raise RuntimeError("db down")

    with pytest.raises(HTTPException) as exc_info:
        await get_all_pending_requests(page=1, size=10, current_user=_admin_user(), db=_RaisingDb())
    assert exc_info.value.status_code == 500


# ── _handle_itv_rejected ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_handle_itv_rejected_sets_status_and_releases_stock(monkeypatch):
    release_mock = AsyncMock()
    monkeypatch.setattr(
        itv_mod, "InventoryReservationService",
        lambda db: SimpleNamespace(release_all=release_mock),
    )
    itv = SimpleNamespace(id=1, statut="PENDING_APPROVAL", rejection_reason=None)
    await _handle_itv_rejected(FakeDb(), itv, "not needed")
    assert itv.statut == "DECLINED"
    assert itv.rejection_reason == "not needed"
    release_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_itv_rejected_swallows_release_failure(monkeypatch):
    monkeypatch.setattr(
        itv_mod, "InventoryReservationService",
        lambda db: SimpleNamespace(release_all=AsyncMock(side_effect=RuntimeError("boom"))),
    )
    itv = SimpleNamespace(id=1, statut="PENDING_APPROVAL", rejection_reason=None)
    await _handle_itv_rejected(FakeDb(), itv, None)  # must not raise
    assert itv.statut == "DECLINED"


# ── _handle_itv_approved ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_handle_itv_approved_success_creates_wo(monkeypatch):
    monkeypatch.setattr(
        itv_mod, "InventoryReservationService",
        lambda db: SimpleNamespace(try_reserve=AsyncMock()),
    )
    itv = SimpleNamespace(
        id=1, statut="PENDING_APPROVAL", parts_approved=False, problem_description="noisy",
        priority="HAUTE", machine_id=5, requested_by=2, requested_at=None,
        estimated_duration_minutes=30, ordre_travail_id=None,
    )
    db = FakeDb([FakeResult(scalar_one_or_none="Press-1")])
    await _handle_itv_approved(db, itv, _admin_user())
    assert itv.statut == "APPROVED"
    assert itv.parts_approved is True
    assert itv.ordre_travail_id == 100
    assert len(db.added) == 1
    assert "Press-1" in db.added[0].titre


@pytest.mark.asyncio
async def test_handle_itv_approved_insufficient_stock_raises_409(monkeypatch):
    missing_item = SimpleNamespace(piece_id=1, piece_name="Belt", requested=2, available=0, deficit=2)
    monkeypatch.setattr(
        itv_mod, "InventoryReservationService",
        lambda db: SimpleNamespace(try_reserve=AsyncMock(side_effect=InsufficientStockError(missing=[missing_item]))),
    )
    itv = SimpleNamespace(id=1, statut="PENDING_APPROVAL", parts_approved=False, problem_description="x", priority="HAUTE", machine_id=5, requested_by=2)
    db = FakeDb()
    with pytest.raises(HTTPException) as exc_info:
        await _handle_itv_approved(db, itv, _admin_user())
    assert exc_info.value.status_code == 409
    assert db.rolled_back == 1


@pytest.mark.asyncio
async def test_handle_itv_approved_reservation_soft_failure_continues(monkeypatch):
    monkeypatch.setattr(
        itv_mod, "InventoryReservationService",
        lambda db: SimpleNamespace(try_reserve=AsyncMock(side_effect=RuntimeError("soft fail"))),
    )
    itv = SimpleNamespace(
        id=1, statut="PENDING_APPROVAL", parts_approved=False, problem_description="x",
        priority="HAUTE", machine_id=5, requested_by=2, requested_at=None,
        estimated_duration_minutes=None, ordre_travail_id=None,
    )
    db = FakeDb([FakeResult(scalar_one_or_none=None)])
    await _handle_itv_approved(db, itv, _admin_user())
    assert itv.statut == "APPROVED"  # continued despite reservation failure


@pytest.mark.asyncio
async def test_handle_itv_approved_swallows_rmq_failure(monkeypatch):
    monkeypatch.setattr(
        itv_mod, "InventoryReservationService",
        lambda db: SimpleNamespace(try_reserve=AsyncMock()),
    )
    monkeypatch.setattr(itv_mod, "get_rabbitmq", AsyncMock(side_effect=RuntimeError("rmq down")))
    itv = SimpleNamespace(
        id=1, statut="PENDING_APPROVAL", parts_approved=False, problem_description="x",
        priority="HAUTE", machine_id=5, requested_by=2, requested_at=None,
        estimated_duration_minutes=None, ordre_travail_id=None,
    )
    db = FakeDb([FakeResult(scalar_one_or_none=None)])
    await _handle_itv_approved(db, itv, _admin_user())  # must not raise
    assert itv.statut == "APPROVED"


# ── validate_itv_request ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_validate_itv_request_non_admin_rejected():
    with pytest.raises(HTTPException) as exc_info:
        await validate_itv_request(
            request_id=1, data=ItvRequestValidation(status="APPROVED"),
            current_user=_non_admin_user(), db=FakeDb(),
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_validate_itv_request_not_found():
    db = FakeDb([FakeResult(scalar_one_or_none=None)])
    with pytest.raises(HTTPException) as exc_info:
        await validate_itv_request(
            request_id=99, data=ItvRequestValidation(status="APPROVED"),
            current_user=_admin_user(), db=db,
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_validate_itv_request_wrong_status():
    itv = SimpleNamespace(id=1, statut="APPROVED")
    db = FakeDb([FakeResult(scalar_one_or_none=itv)])
    with pytest.raises(HTTPException) as exc_info:
        await validate_itv_request(
            request_id=1, data=ItvRequestValidation(status="APPROVED"),
            current_user=_admin_user(), db=db,
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_validate_itv_request_rejected_success(monkeypatch):
    monkeypatch.setattr(
        itv_mod, "InventoryReservationService",
        lambda db: SimpleNamespace(release_all=AsyncMock()),
    )
    itv = SimpleNamespace(
        id=1, statut="PENDING_APPROVAL", approved_by=None, approved_at=None, rejection_reason=None,
    )
    db = FakeDb([FakeResult(scalar_one_or_none=itv)])
    result = await validate_itv_request(
        request_id=1, data=ItvRequestValidation(status="REJECTED", rejection_reason="no need"),
        current_user=_admin_user(), db=db,
    )
    assert itv.statut == "DECLINED"
    assert db.committed == 1
    assert "DECLINED" in result["message"]


@pytest.mark.asyncio
async def test_validate_itv_request_unexpected_exception_rolls_back(monkeypatch):
    itv = SimpleNamespace(id=1, statut="PENDING_APPROVAL", approved_by=None, approved_at=None)

    async def _raise(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(itv_mod, "_handle_itv_approved", _raise)
    db = FakeDb([FakeResult(scalar_one_or_none=itv)])
    with pytest.raises(HTTPException) as exc_info:
        await validate_itv_request(
            request_id=1, data=ItvRequestValidation(status="APPROVED"),
            current_user=_admin_user(), db=db,
        )
    assert exc_info.value.status_code == 500
    assert db.rolled_back == 1
