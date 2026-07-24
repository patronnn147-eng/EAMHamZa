"""Unit tests for app/backend/modules/chetop/routes/work_orders.py."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from models.alertes import Alert  # noqa: F401 — registers Alert mapper (needed by Utilisateurs relationship)
import modules.chetop.routes.work_orders as chetop_mod
from models.utilisateurs import UserRole
from modules.chetop.routes.work_orders import (
    WorkOrderCompletePayload,
    complete_work_order,
    get_my_work_orders,
    start_work_order,
)


class FakeResult:
    def __init__(self, scalar_one_or_none=None, scalar_value=None, all_rows=None):
        self._soo = scalar_one_or_none
        self._scalar_value = scalar_value
        self._all_rows = all_rows

    def scalar_one_or_none(self):
        return self._soo

    def scalar(self):
        return self._scalar_value

    def all(self):
        return self._all_rows or []


class FakeSession:
    def __init__(self, execute_results=None, scalars=None):
        self._results = list(execute_results or [])
        self._scalars = list(scalars or [])
        self.committed = 0
        self.rolled_back = 0
        self.added = []

    async def execute(self, *_a, **_k):
        return self._results.pop(0)

    async def scalar(self, *_a, **_k):
        return self._scalars.pop(0)

    async def commit(self):
        self.committed += 1

    async def rollback(self):
        self.rolled_back += 1

    def add(self, obj):
        self.added.append(obj)


def _chetop_user(id=1, nom="Alice"):
    return SimpleNamespace(id=id, nom=nom, role=UserRole.CHETOP)


def _other_role_user():
    return SimpleNamespace(id=1, nom="Bob", role=UserRole.TECHNICIEN)


def _wo(id=1, statut="ASSIGNÉ", machine_id=10):
    return SimpleNamespace(
        id=id, statut=statut, machine_id=machine_id, titre="WO1",
        date_debut=None, date_fin=None, rapport=None, health_score_at_completion=None,
    )


def _payload(**overrides):
    base = dict(rapport="All fixed")
    base.update(overrides)
    return WorkOrderCompletePayload(**base)


@pytest.fixture(autouse=True)
def _stub_audit_and_snapshot(monkeypatch):
    monkeypatch.setattr(chetop_mod, "AuditService", lambda db: SimpleNamespace(log_update=AsyncMock()))
    monkeypatch.setattr(
        chetop_mod, "PostMaintenanceRecoveryService",
        lambda db: SimpleNamespace(snapshot_health=AsyncMock(return_value=None)),
    )


# ── get_my_work_orders ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_my_work_orders_non_chetop_rejected():
    with pytest.raises(HTTPException) as exc_info:
        await get_my_work_orders(page=1, size=10, current_user=_other_role_user(), db=FakeSession())
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_my_work_orders_empty():
    db = FakeSession([FakeResult(scalar_value=0), FakeResult(all_rows=[])])
    result = await get_my_work_orders(page=1, size=10, current_user=_chetop_user(), db=db)
    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_get_my_work_orders_maps_rows():
    wo = _wo()
    wo.description = "desc"
    wo.priorite = "HAUTE"
    wo.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    db = FakeSession([FakeResult(scalar_value=1), FakeResult(all_rows=[(wo, "Press-1")])])
    result = await get_my_work_orders(page=1, size=10, current_user=_chetop_user(), db=db)
    assert result.items[0].machine_nom == "Press-1"


@pytest.mark.asyncio
async def test_get_my_work_orders_exception_raises_500():
    class _RaisingSession(FakeSession):
        async def execute(self, *_a, **_k):
            raise RuntimeError("db down")

    with pytest.raises(HTTPException) as exc_info:
        await get_my_work_orders(page=1, size=10, current_user=_chetop_user(), db=_RaisingSession())
    assert exc_info.value.status_code == 500


# ── start_work_order ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_start_work_order_non_chetop_rejected():
    with pytest.raises(HTTPException) as exc_info:
        await start_work_order(order_id=1, current_user=_other_role_user(), db=FakeSession())
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_start_work_order_not_requester():
    db = FakeSession([FakeResult(scalar_one_or_none=None)])
    with pytest.raises(HTTPException) as exc_info:
        await start_work_order(order_id=1, current_user=_chetop_user(), db=db)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_start_work_order_not_found():
    db = FakeSession([
        FakeResult(scalar_one_or_none=SimpleNamespace()),  # ownership check passes
        FakeResult(scalar_one_or_none=None),  # WO lookup fails
    ])
    with pytest.raises(HTTPException) as exc_info:
        await start_work_order(order_id=1, current_user=_chetop_user(), db=db)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_start_work_order_wrong_status():
    wo = _wo(statut="EN_COURS")
    db = FakeSession([FakeResult(scalar_one_or_none=SimpleNamespace()), FakeResult(scalar_one_or_none=wo)])
    with pytest.raises(HTTPException) as exc_info:
        await start_work_order(order_id=1, current_user=_chetop_user(), db=db)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_start_work_order_success():
    wo = _wo(statut="ASSIGNÉ")
    db = FakeSession([FakeResult(scalar_one_or_none=SimpleNamespace()), FakeResult(scalar_one_or_none=wo)])
    result = await start_work_order(order_id=1, current_user=_chetop_user(), db=db)
    assert result == {"message": "Work order started", "statut": "EN_COURS"}
    assert wo.statut == "EN_COURS"
    assert wo.date_debut is not None
    assert db.committed == 1


@pytest.mark.asyncio
async def test_start_work_order_unexpected_exception_rolls_back():
    class _FailingSession(FakeSession):
        def __init__(self):
            super().__init__([FakeResult(scalar_one_or_none=SimpleNamespace())])
            self._calls = 0

        async def execute(self, *_a, **_k):
            self._calls += 1
            if self._calls == 1:
                return self._results.pop(0)
            raise RuntimeError("boom")

    db = _FailingSession()
    with pytest.raises(HTTPException) as exc_info:
        await start_work_order(order_id=1, current_user=_chetop_user(), db=db)
    assert exc_info.value.status_code == 500
    assert db.rolled_back == 1


# ── complete_work_order ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_complete_work_order_non_chetop_rejected():
    with pytest.raises(HTTPException) as exc_info:
        await complete_work_order(order_id=1, payload=_payload(), current_user=_other_role_user(), db=FakeSession())
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_complete_work_order_not_requester():
    db = FakeSession([FakeResult(scalar_one_or_none=None)])
    with pytest.raises(HTTPException) as exc_info:
        await complete_work_order(order_id=1, payload=_payload(), current_user=_chetop_user(), db=db)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_complete_work_order_not_found():
    intervention = SimpleNamespace(id=1)
    db = FakeSession([
        FakeResult(scalar_one_or_none=intervention),
        FakeResult(scalar_one_or_none=None),
    ])
    with pytest.raises(HTTPException) as exc_info:
        await complete_work_order(order_id=1, payload=_payload(), current_user=_chetop_user(), db=db)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_complete_work_order_wrong_status():
    intervention = SimpleNamespace(id=1)
    wo = _wo(statut="ASSIGNÉ")
    db = FakeSession([FakeResult(scalar_one_or_none=intervention), FakeResult(scalar_one_or_none=wo)])
    with pytest.raises(HTTPException) as exc_info:
        await complete_work_order(order_id=1, payload=_payload(), current_user=_chetop_user(), db=db)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_complete_work_order_success_minimal():
    intervention = SimpleNamespace(
        id=1, statut="EN_COURS", date_debut=None, date_fin=None,
    )
    wo = _wo(statut="EN_COURS")
    db = FakeSession(
        execute_results=[
            FakeResult(scalar_one_or_none=intervention),
            FakeResult(scalar_one_or_none=wo),
        ],
        scalars=[None],  # machine lookup -> not found
    )
    result = await complete_work_order(order_id=1, payload=_payload(), current_user=_chetop_user(), db=db)
    assert result == {"message": "Work order completed", "statut": "TERMINÉ"}
    assert wo.statut == "TERMINÉ"
    assert intervention.statut == "TERMINÉ"
    assert db.committed == 1


@pytest.mark.asyncio
async def test_complete_work_order_updates_machine_and_adds_telemetry():
    intervention = SimpleNamespace(id=1, statut="EN_COURS", date_debut=None, date_fin=None)
    wo = _wo(statut="EN_COURS")
    machine = SimpleNamespace(date_derniere_maintenance=None)
    db = FakeSession(
        execute_results=[
            FakeResult(scalar_one_or_none=intervention),
            FakeResult(scalar_one_or_none=wo),
        ],
        scalars=[machine],
    )
    payload = _payload(air_temperature=300.0)
    await complete_work_order(order_id=1, payload=payload, current_user=_chetop_user(), db=db)
    assert machine.date_derniere_maintenance is not None
    assert len(db.added) == 1


@pytest.mark.asyncio
async def test_complete_work_order_swallows_status_change_request_failure(monkeypatch):
    intervention = SimpleNamespace(id=1, statut="EN_COURS", date_debut=None, date_fin=None)
    wo = _wo(statut="EN_COURS")
    db = FakeSession(
        execute_results=[
            FakeResult(scalar_one_or_none=intervention),
            FakeResult(scalar_one_or_none=wo),
        ],
        scalars=[None],
    )
    monkeypatch.setattr(
        chetop_mod, "create_status_change_request",
        AsyncMock(side_effect=RuntimeError("boom")),
    )
    result = await complete_work_order(
        order_id=1, payload=_payload(machine_status_after="EN_PANNE"),
        current_user=_chetop_user(), db=db,
    )
    assert result["statut"] == "TERMINÉ"


@pytest.mark.asyncio
async def test_complete_work_order_unexpected_exception_rolls_back():
    intervention = SimpleNamespace(id=1)

    class _FailingSession(FakeSession):
        def __init__(self):
            super().__init__([FakeResult(scalar_one_or_none=intervention)])
            self._calls = 0

        async def execute(self, *_a, **_k):
            self._calls += 1
            if self._calls == 1:
                return self._results.pop(0)
            raise RuntimeError("boom")

    db = _FailingSession()
    with pytest.raises(HTTPException) as exc_info:
        await complete_work_order(order_id=1, payload=_payload(), current_user=_chetop_user(), db=db)
    assert exc_info.value.status_code == 500
    assert db.rolled_back == 1
