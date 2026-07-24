"""Unit tests for the route handlers in
app/backend/modules/technicien/technicien_work_orders.py (get_my_work_orders,
start_work_order, complete_work_order) — see technicien_work_orders_helpers.test.py
for the private helper functions these routes delegate to."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from models.alertes import Alert  # noqa: F401 — registers Alert mapper (needed by Utilisateurs relationship)
import modules.technicien.technicien_work_orders as wo_mod
from modules.technicien.technicien_work_orders import (
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


def _wo(id=1, statut="ASSIGNED", utilisateur_id=1, machine_id=10, titre="WO1", date_debut=None, date_fin=None):
    return SimpleNamespace(
        id=id, statut=statut, utilisateur_id=utilisateur_id, machine_id=machine_id,
        titre=titre, date_debut=date_debut, date_fin=date_fin, rapport=None,
        health_score_at_completion=None,
    )


def _user(id=1, nom="Bob"):
    return SimpleNamespace(id=id, nom=nom)


@pytest.fixture(autouse=True)
def _stub_audit(monkeypatch):
    """Every route calls the fire-and-forget audit helpers; stub AuditService
    so tests don't depend on its real DB-write behavior (covered separately
    in technicien_work_orders_helpers.test.py)."""
    monkeypatch.setattr(wo_mod, "AuditService", lambda db: SimpleNamespace(log_update=AsyncMock()))
    monkeypatch.setattr(
        wo_mod, "PostMaintenanceRecoveryService",
        lambda db: SimpleNamespace(snapshot_health=AsyncMock(return_value=None)),
    )


# ── get_my_work_orders ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_my_work_orders_empty():
    user = _user()
    db = FakeSession([FakeResult(scalar_value=0), FakeResult(all_rows=[])])
    result = await get_my_work_orders(page=1, size=10, current_user=user, db=db)
    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_get_my_work_orders_maps_rows():
    user = _user()
    wo = _wo()
    wo.description = "desc"
    wo.priorite = "HAUTE"
    wo.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    wo.date_echeance = None
    db = FakeSession([
        FakeResult(scalar_value=1),
        FakeResult(all_rows=[(wo, "Press-1")]),
    ])
    result = await get_my_work_orders(page=1, size=10, current_user=user, db=db)
    assert result.total == 1
    assert result.items[0].machine_nom == "Press-1"


@pytest.mark.asyncio
async def test_get_my_work_orders_exception_raises_500():
    user = _user()

    class _RaisingSession(FakeSession):
        async def execute(self, *_a, **_k):
            raise RuntimeError("db down")

    db = _RaisingSession([])
    with pytest.raises(HTTPException) as exc_info:
        await get_my_work_orders(page=1, size=10, current_user=user, db=db)
    assert exc_info.value.status_code == 500


# ── start_work_order ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_start_work_order_not_found():
    db = FakeSession([FakeResult(scalar_one_or_none=None)])
    with pytest.raises(HTTPException) as exc_info:
        await start_work_order(order_id=99, current_user=_user(), db=db)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_start_work_order_access_denied():
    wo = _wo(utilisateur_id=999)
    db = FakeSession([
        FakeResult(scalar_one_or_none=wo),
        FakeResult(scalar_one_or_none=None),  # _check_wo_access intervention lookup
    ])
    with pytest.raises(HTTPException) as exc_info:
        await start_work_order(order_id=1, current_user=_user(id=1), db=db)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_start_work_order_wrong_status():
    wo = _wo(statut="COMPLETED", utilisateur_id=1)
    db = FakeSession([FakeResult(scalar_one_or_none=wo)])
    with pytest.raises(HTTPException) as exc_info:
        await start_work_order(order_id=1, current_user=_user(id=1), db=db)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_start_work_order_success_no_intervention():
    wo = _wo(statut="ASSIGNED", utilisateur_id=1)
    db = FakeSession([
        FakeResult(scalar_one_or_none=wo),
        FakeResult(scalar_one_or_none=None),  # no linked intervention
    ])
    result = await start_work_order(order_id=1, current_user=_user(id=1), db=db)
    assert result["message"] == "Work order started"
    assert db.committed == 1


@pytest.mark.asyncio
async def test_start_work_order_success_updates_linked_intervention():
    wo = _wo(statut="EN_ATTENTE", utilisateur_id=1)
    intervention = SimpleNamespace(statut="APPROVED", date_debut=None)
    db = FakeSession([
        FakeResult(scalar_one_or_none=wo),
        FakeResult(scalar_one_or_none=intervention),
    ])
    await start_work_order(order_id=1, current_user=_user(id=1), db=db)
    assert intervention.statut == "EN_COURS"


@pytest.mark.asyncio
async def test_start_work_order_unexpected_exception_rolls_back():
    wo = _wo(statut="ASSIGNED", utilisateur_id=1)

    class _FailingOnSecondExecute(FakeSession):
        def __init__(self):
            super().__init__([FakeResult(scalar_one_or_none=wo)])
            self._calls = 0

        async def execute(self, *_a, **_k):
            self._calls += 1
            if self._calls == 1:
                return self._results.pop(0)
            raise RuntimeError("boom")

    db = _FailingOnSecondExecute()
    with pytest.raises(HTTPException) as exc_info:
        await start_work_order(order_id=1, current_user=_user(id=1), db=db)
    assert exc_info.value.status_code == 500
    assert db.rolled_back == 1


# ── complete_work_order ──────────────────────────────────────────────────────

def _payload(**overrides):
    base = dict(rapport="All fixed")
    base.update(overrides)
    return WorkOrderCompletePayload(**base)


@pytest.mark.asyncio
async def test_complete_work_order_not_found():
    db = FakeSession([FakeResult(scalar_one_or_none=None)])
    with pytest.raises(HTTPException) as exc_info:
        await complete_work_order(order_id=99, payload=_payload(), current_user=_user(), db=db)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_complete_work_order_access_denied():
    wo = _wo(utilisateur_id=999, statut="IN_PROGRESS")
    db = FakeSession([
        FakeResult(scalar_one_or_none=wo),
        FakeResult(scalar_one_or_none=None),  # _check_wo_access lookup
    ])
    with pytest.raises(HTTPException) as exc_info:
        await complete_work_order(order_id=1, payload=_payload(), current_user=_user(id=1), db=db)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_complete_work_order_wrong_status():
    wo = _wo(utilisateur_id=1, statut="ASSIGNED")
    db = FakeSession([FakeResult(scalar_one_or_none=wo)])
    with pytest.raises(HTTPException) as exc_info:
        await complete_work_order(order_id=1, payload=_payload(), current_user=_user(id=1), db=db)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_complete_work_order_success_minimal():
    wo = _wo(utilisateur_id=1, statut="IN_PROGRESS")
    db = FakeSession(
        execute_results=[
            FakeResult(scalar_one_or_none=wo),
            FakeResult(scalar_one_or_none=None),  # no linked intervention
        ],
        scalars=[None],  # machine lookup -> not found, skipped update
    )
    result = await complete_work_order(order_id=1, payload=_payload(), current_user=_user(id=1), db=db)
    assert result["statut"] == "TERMINÉ"
    assert db.committed == 1
    assert wo.statut == "COMPLETED"


@pytest.mark.asyncio
async def test_complete_work_order_updates_intervention_and_machine(monkeypatch):
    wo = _wo(utilisateur_id=1, statut="IN_PROGRESS")
    intervention = SimpleNamespace(
        id=5, statut="EN_COURS", date_debut=None, date_fin=None, planning_tache_id=None,
        legacy_parts_text=None, ml_prediction_matched=None,
    )
    machine = SimpleNamespace(date_derniere_maintenance=None)
    db = FakeSession(
        execute_results=[
            FakeResult(scalar_one_or_none=wo),
            FakeResult(scalar_one_or_none=intervention),
        ],
        scalars=[machine],
    )
    result = await complete_work_order(
        order_id=1, payload=_payload(machine_status_after="OPERATIONNELLE"),
        current_user=_user(id=1), db=db,
    )
    assert intervention.statut == "TERMINÉ"
    assert machine.date_derniere_maintenance is not None
    assert result["statut"] == "TERMINÉ"


@pytest.mark.asyncio
async def test_complete_work_order_swallows_status_change_request_failure(monkeypatch):
    wo = _wo(utilisateur_id=1, statut="IN_PROGRESS")
    intervention = SimpleNamespace(
        id=5, statut="EN_COURS", date_debut=None, date_fin=None, planning_tache_id=None,
        legacy_parts_text=None, ml_prediction_matched=None,
    )
    db = FakeSession(
        execute_results=[
            FakeResult(scalar_one_or_none=wo),
            FakeResult(scalar_one_or_none=intervention),
        ],
        scalars=[None],
    )
    monkeypatch.setattr(
        wo_mod, "create_status_change_request",
        AsyncMock(side_effect=RuntimeError("boom")),
    )
    result = await complete_work_order(
        order_id=1, payload=_payload(machine_status_after="EN_PANNE"),
        current_user=_user(id=1), db=db,
    )
    assert result["statut"] == "TERMINÉ"  # non-fatal, request failure swallowed


@pytest.mark.asyncio
async def test_complete_work_order_unexpected_exception_rolls_back():
    wo = _wo(utilisateur_id=1, statut="IN_PROGRESS")

    class _FailingSession(FakeSession):
        def __init__(self):
            super().__init__([FakeResult(scalar_one_or_none=wo)])
            self._calls = 0

        async def execute(self, *_a, **_k):
            self._calls += 1
            if self._calls == 1:
                return self._results.pop(0)
            raise RuntimeError("boom")

    db = _FailingSession()
    with pytest.raises(HTTPException) as exc_info:
        await complete_work_order(order_id=1, payload=_payload(), current_user=_user(id=1), db=db)
    assert exc_info.value.status_code == 500
    assert db.rolled_back == 1
