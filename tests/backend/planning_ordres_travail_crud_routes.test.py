"""Unit tests for app/backend/modules/shared/routes/planning_ordres_travail/crud.py.
PlanningOrdresTravailService is mocked to isolate route-level logic —
same generated-CRUD-template shape as ordres_travail_crud_routes.test.py,
plus create_planning_OrdresTravail's extra ADMIN/CHETOP/CHEFTECH access
control. Regression coverage for two real bugs found while writing these
tests: the 400-becomes-500 missing-guard bug (same family as commit
d65fba5) and a `UserRole.CHEFOP` typo (real enum member is `CHETOP`) that
raised an unhandled AttributeError for every non-admin caller."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

import modules.shared.routes.planning_ordres_travail.crud as crud_mod
from models.utilisateurs import UserRole
from modules.shared.routes.planning_ordres_travail.crud import (
    PlanningOrdresTravailBatchCreateRequest,
    PlanningOrdresTravailBatchDeleteRequest,
    PlanningOrdresTravailBatchUpdateRequest,
    PlanningOrdresTravailData,
    PlanningOrdresTravailUpdateData,
    create_planning_OrdresTravail,
    create_planning_OrdresTravails_batch,
    delete_planning_OrdresTravail,
    delete_planning_OrdresTravails_batch,
    get_planning_OrdresTravail,
    query_planning_OrdresTravails,
    query_planning_OrdresTravails_all,
    update_planning_OrdresTravail,
    update_planning_OrdresTravails_batch,
)


class FakeResult:
    def __init__(self, scalar_one_or_none=None):
        self._soo = scalar_one_or_none

    def scalar_one_or_none(self):
        return self._soo


class FakeDb:
    def __init__(self, execute_results=None):
        self._results = list(execute_results or [])
        self.rolled_back = 0

    async def execute(self, *_a, **_k):
        return self._results.pop(0)

    async def rollback(self):
        self.rolled_back += 1


def _fake_service(**overrides):
    base = dict(
        get_list=AsyncMock(return_value={"items": [], "total": 0, "skip": 0, "limit": 20}),
        get_by_id=AsyncMock(return_value=None),
        create=AsyncMock(return_value=None),
        update=AsyncMock(return_value=None),
        delete=AsyncMock(return_value=False),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _admin_user():
    return SimpleNamespace(id=1, email="a@x.com", role=UserRole.ADMIN)


def _chetop_user():
    return SimpleNamespace(id=1, email="a@x.com", role=UserRole.CHETOP)


def _data(**overrides):
    base = dict(planning_id=1)
    base.update(overrides)
    return PlanningOrdresTravailData(**base)


# ── query / query_all ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_query_delegates(monkeypatch):
    svc = _fake_service(get_list=AsyncMock(return_value={"items": [], "total": 3, "skip": 0, "limit": 20}))
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: svc)
    result = await query_planning_OrdresTravails(
        query=None, sort=None, skip=0, limit=20, fields=None, current_user=_admin_user(), db=FakeDb(),
    )
    assert result["total"] == 3


@pytest.mark.asyncio
async def test_query_invalid_json_raises_400(monkeypatch):
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: _fake_service())
    with pytest.raises(HTTPException) as exc_info:
        await query_planning_OrdresTravails(
            query="{bad", sort=None, skip=0, limit=20, fields=None, current_user=_admin_user(), db=FakeDb(),
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_query_exception_raises_500(monkeypatch):
    svc = _fake_service(get_list=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: svc)
    with pytest.raises(HTTPException) as exc_info:
        await query_planning_OrdresTravails(
            query=None, sort=None, skip=0, limit=20, fields=None, current_user=_admin_user(), db=FakeDb(),
        )
    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_query_all_variant_delegates(monkeypatch):
    svc = _fake_service()
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: svc)
    result = await query_planning_OrdresTravails_all(
        query=None, sort=None, skip=0, limit=20, fields=None, current_user=_admin_user(), db=FakeDb(),
    )
    assert result["items"] == []


# ── get ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_found(monkeypatch):
    obj = SimpleNamespace(id=1)
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: _fake_service(get_by_id=AsyncMock(return_value=obj)))
    assert await get_planning_OrdresTravail(id=1, fields=None, db=FakeDb()) is obj


@pytest.mark.asyncio
async def test_get_not_found_raises_404(monkeypatch):
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: _fake_service())
    with pytest.raises(HTTPException) as exc_info:
        await get_planning_OrdresTravail(id=99, fields=None, db=FakeDb())
    assert exc_info.value.status_code == 404


# ── create (with access-control) ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_admin_bypasses_access_check(monkeypatch):
    obj = SimpleNamespace(id=1)
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: _fake_service(create=AsyncMock(return_value=obj)))
    result = await create_planning_OrdresTravail(data=_data(), current_user=_admin_user(), db=FakeDb())
    assert result is obj


@pytest.mark.asyncio
async def test_create_non_admin_planning_not_found_raises_404():
    db = FakeDb([FakeResult(scalar_one_or_none=None)])
    with pytest.raises(HTTPException) as exc_info:
        await create_planning_OrdresTravail(data=_data(), current_user=_chetop_user(), db=db)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_create_chetop_owner_has_access(monkeypatch):
    # Regression: real code compared current_user.role to the nonexistent
    # UserRole.CHEFOP (typo for CHETOP) — every CHETOP user hit an unhandled
    # AttributeError here before reaching this ownership check at all.
    planning = SimpleNamespace(id=1, chef_operation_id=1, chef_technique_id=None)
    obj = SimpleNamespace(id=5)
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: _fake_service(create=AsyncMock(return_value=obj)))
    db = FakeDb([FakeResult(scalar_one_or_none=planning)])
    result = await create_planning_OrdresTravail(data=_data(), current_user=_chetop_user(), db=db)
    assert result is obj


@pytest.mark.asyncio
async def test_create_non_owner_without_assignment_raises_403():
    planning = SimpleNamespace(id=1, chef_operation_id=999, chef_technique_id=None)
    db = FakeDb([FakeResult(scalar_one_or_none=planning), FakeResult(scalar_one_or_none=None)])
    with pytest.raises(HTTPException) as exc_info:
        await create_planning_OrdresTravail(data=_data(), current_user=_chetop_user(), db=db)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_create_non_owner_with_assignment_has_access(monkeypatch):
    planning = SimpleNamespace(id=1, chef_operation_id=999, chef_technique_id=None)
    assignment = SimpleNamespace(id=1)
    obj = SimpleNamespace(id=5)
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: _fake_service(create=AsyncMock(return_value=obj)))
    db = FakeDb([FakeResult(scalar_one_or_none=planning), FakeResult(scalar_one_or_none=assignment)])
    result = await create_planning_OrdresTravail(data=_data(), current_user=_chetop_user(), db=db)
    assert result is obj


@pytest.mark.asyncio
async def test_create_returns_none_raises_400_not_500(monkeypatch):
    # Regression: this route was missing `except HTTPException: raise` (fixed
    # alongside sibling create_OrdresTravail/create_OrdresIntervention bugs).
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: _fake_service())
    with pytest.raises(HTTPException) as exc_info:
        await create_planning_OrdresTravail(data=_data(), current_user=_admin_user(), db=FakeDb())
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_create_value_error_raises_400(monkeypatch):
    svc = _fake_service(create=AsyncMock(side_effect=ValueError("bad")))
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: svc)
    with pytest.raises(HTTPException) as exc_info:
        await create_planning_OrdresTravail(data=_data(), current_user=_admin_user(), db=FakeDb())
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_create_generic_exception_raises_500(monkeypatch):
    svc = _fake_service(create=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: svc)
    with pytest.raises(HTTPException) as exc_info:
        await create_planning_OrdresTravail(data=_data(), current_user=_admin_user(), db=FakeDb())
    assert exc_info.value.status_code == 500


# ── batch create ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_create_success(monkeypatch):
    obj1, obj2 = SimpleNamespace(id=1), SimpleNamespace(id=2)
    svc = _fake_service(create=AsyncMock(side_effect=[obj1, obj2]))
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: svc)
    request = PlanningOrdresTravailBatchCreateRequest(items=[_data(), _data()])
    result = await create_planning_OrdresTravails_batch(request=request, db=FakeDb())
    assert result == [obj1, obj2]


@pytest.mark.asyncio
async def test_batch_create_exception_rolls_back(monkeypatch):
    svc = _fake_service(create=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: svc)
    db = FakeDb()
    request = PlanningOrdresTravailBatchCreateRequest(items=[_data()])
    with pytest.raises(HTTPException) as exc_info:
        await create_planning_OrdresTravails_batch(request=request, db=db)
    assert exc_info.value.status_code == 500
    assert db.rolled_back == 1


# ── batch update ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_update_success(monkeypatch):
    obj = SimpleNamespace(id=1)
    svc = _fake_service(update=AsyncMock(return_value=obj))
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: svc)
    request = PlanningOrdresTravailBatchUpdateRequest(items=[
        {"id": 1, "updates": PlanningOrdresTravailUpdateData(ordre_travail_id=5)},
    ])
    result = await update_planning_OrdresTravails_batch(request=request, db=FakeDb())
    assert result == [obj]


@pytest.mark.asyncio
async def test_batch_update_exception_rolls_back(monkeypatch):
    svc = _fake_service(update=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: svc)
    db = FakeDb()
    request = PlanningOrdresTravailBatchUpdateRequest(items=[
        {"id": 1, "updates": PlanningOrdresTravailUpdateData(ordre_travail_id=5)},
    ])
    with pytest.raises(HTTPException) as exc_info:
        await update_planning_OrdresTravails_batch(request=request, db=db)
    assert exc_info.value.status_code == 500
    assert db.rolled_back == 1


# ── update ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_success(monkeypatch):
    obj = SimpleNamespace(id=1)
    svc = _fake_service(update=AsyncMock(return_value=obj))
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: svc)
    result = await update_planning_OrdresTravail(id=1, data=PlanningOrdresTravailUpdateData(ordre_travail_id=5), db=FakeDb())
    assert result is obj


@pytest.mark.asyncio
async def test_update_not_found_raises_404(monkeypatch):
    svc = _fake_service(update=AsyncMock(return_value=None))
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: svc)
    with pytest.raises(HTTPException) as exc_info:
        await update_planning_OrdresTravail(id=99, data=PlanningOrdresTravailUpdateData(), db=FakeDb())
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_value_error_raises_400(monkeypatch):
    svc = _fake_service(update=AsyncMock(side_effect=ValueError("bad")))
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: svc)
    with pytest.raises(HTTPException) as exc_info:
        await update_planning_OrdresTravail(id=1, data=PlanningOrdresTravailUpdateData(), db=FakeDb())
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_update_generic_exception_raises_500(monkeypatch):
    svc = _fake_service(update=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: svc)
    with pytest.raises(HTTPException) as exc_info:
        await update_planning_OrdresTravail(id=1, data=PlanningOrdresTravailUpdateData(), db=FakeDb())
    assert exc_info.value.status_code == 500


# ── batch delete ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_delete_counts_successes(monkeypatch):
    svc = _fake_service(delete=AsyncMock(side_effect=[True, False]))
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: svc)
    request = PlanningOrdresTravailBatchDeleteRequest(ids=[1, 2])
    result = await delete_planning_OrdresTravails_batch(request=request, db=FakeDb())
    assert result["deleted_count"] == 1


@pytest.mark.asyncio
async def test_batch_delete_exception_rolls_back(monkeypatch):
    svc = _fake_service(delete=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: svc)
    db = FakeDb()
    request = PlanningOrdresTravailBatchDeleteRequest(ids=[1])
    with pytest.raises(HTTPException) as exc_info:
        await delete_planning_OrdresTravails_batch(request=request, db=db)
    assert exc_info.value.status_code == 500
    assert db.rolled_back == 1


# ── delete ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_success(monkeypatch):
    svc = _fake_service(delete=AsyncMock(return_value=True))
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: svc)
    result = await delete_planning_OrdresTravail(id=1, db=FakeDb())
    assert result == {"message": "PlanningOrdresTravail deleted successfully", "id": 1}


@pytest.mark.asyncio
async def test_delete_not_found_raises_404(monkeypatch):
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: _fake_service())
    with pytest.raises(HTTPException) as exc_info:
        await delete_planning_OrdresTravail(id=99, db=FakeDb())
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_exception_raises_500(monkeypatch):
    svc = _fake_service(delete=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(crud_mod, "PlanningOrdresTravailService", lambda db: svc)
    with pytest.raises(HTTPException) as exc_info:
        await delete_planning_OrdresTravail(id=1, db=FakeDb())
    assert exc_info.value.status_code == 500
