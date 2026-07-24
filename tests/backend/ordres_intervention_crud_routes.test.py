"""Unit tests for app/backend/modules/shared/routes/ordres_intervention/crud.py.
OrdresInterventionService is mocked — same route-level focus as
ordres_travail_crud_routes.test.py (JSON query parsing, HTTP status
mapping, batch loops, non-fatal audit-log failures)."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

import modules.shared.routes.ordres_intervention.crud as crud_mod
from modules.shared.routes.ordres_intervention.crud import (
    OrdresInterventionBatchCreateRequest,
    OrdresInterventionBatchDeleteRequest,
    OrdresInterventionBatchUpdateRequest,
    OrdresInterventionData,
    OrdresInterventionUpdateData,
    create_OrdresIntervention,
    create_OrdresInterventions_batch,
    delete_OrdresIntervention,
    delete_OrdresInterventions_batch,
    get_OrdresIntervention,
    query_OrdresInterventions,
    query_OrdresInterventions_all,
    update_OrdresIntervention,
    update_OrdresInterventions_batch,
)


class FakeDb:
    def __init__(self):
        self.rolled_back = 0

    async def rollback(self):
        self.rolled_back += 1


def _user():
    return SimpleNamespace(id=1, nom="Bob")


@pytest.fixture(autouse=True)
def _stub_audit(monkeypatch):
    monkeypatch.setattr(
        crud_mod, "AuditService",
        lambda db: SimpleNamespace(
            log_create=AsyncMock(), log_update=AsyncMock(), log_delete=AsyncMock(),
        ),
    )


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


# ── query_OrdresInterventions / _all ────────────────────────────────────────

@pytest.mark.asyncio
async def test_query_no_filter_delegates(monkeypatch):
    svc = _fake_service(get_list=AsyncMock(return_value={"items": [], "total": 3, "skip": 0, "limit": 20}))
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: svc)
    result = await query_OrdresInterventions(query=None, sort=None, skip=0, limit=20, fields=None, db=FakeDb())
    assert result["total"] == 3


@pytest.mark.asyncio
async def test_query_invalid_json_raises_400(monkeypatch):
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: _fake_service())
    with pytest.raises(HTTPException) as exc_info:
        await query_OrdresInterventions(query="{bad", sort=None, skip=0, limit=20, fields=None, db=FakeDb())
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_query_valid_json_parses_query_dict(monkeypatch):
    svc = _fake_service()
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: svc)
    await query_OrdresInterventions(query='{"statut": "EN_COURS"}', sort="-id", skip=0, limit=20, fields=None, db=FakeDb())
    svc.get_list.assert_awaited_once_with(skip=0, limit=20, query_dict={"statut": "EN_COURS"}, sort="-id")


@pytest.mark.asyncio
async def test_query_service_exception_raises_500(monkeypatch):
    svc = _fake_service(get_list=AsyncMock(side_effect=RuntimeError("db down")))
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: svc)
    with pytest.raises(HTTPException) as exc_info:
        await query_OrdresInterventions(query=None, sort=None, skip=0, limit=20, fields=None, db=FakeDb())
    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_query_all_variant_delegates(monkeypatch):
    svc = _fake_service()
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: svc)
    result = await query_OrdresInterventions_all(query=None, sort=None, skip=0, limit=20, fields=None, db=FakeDb())
    assert result["items"] == []


@pytest.mark.asyncio
async def test_query_all_invalid_json_raises_400(monkeypatch):
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: _fake_service())
    with pytest.raises(HTTPException) as exc_info:
        await query_OrdresInterventions_all(query="{bad", sort=None, skip=0, limit=20, fields=None, db=FakeDb())
    assert exc_info.value.status_code == 400


# ── get_OrdresIntervention ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_found(monkeypatch):
    itv = SimpleNamespace(id=1)
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: _fake_service(get_by_id=AsyncMock(return_value=itv)))
    result = await get_OrdresIntervention(id=1, fields=None, db=FakeDb())
    assert result is itv


@pytest.mark.asyncio
async def test_get_not_found_raises_404(monkeypatch):
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: _fake_service())
    with pytest.raises(HTTPException) as exc_info:
        await get_OrdresIntervention(id=99, fields=None, db=FakeDb())
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_exception_raises_500(monkeypatch):
    svc = _fake_service(get_by_id=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: svc)
    with pytest.raises(HTTPException) as exc_info:
        await get_OrdresIntervention(id=1, fields=None, db=FakeDb())
    assert exc_info.value.status_code == 500


# ── create_OrdresIntervention ────────────────────────────────────────────────

def _data(**overrides):
    base = dict(date_intervention=datetime(2026, 1, 1))
    base.update(overrides)
    return OrdresInterventionData(**base)


@pytest.mark.asyncio
async def test_create_success(monkeypatch):
    itv = SimpleNamespace(id=1, titre="Fix pump")
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: _fake_service(create=AsyncMock(return_value=itv)))
    data = _data()
    result = await create_OrdresIntervention(data=data, db=FakeDb(), current_user=_user())
    assert result is itv
    assert data.statut == "EN_ATTENTE"


@pytest.mark.asyncio
async def test_create_audit_failure_swallowed(monkeypatch):
    itv = SimpleNamespace(id=1, titre="Fix pump")
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: _fake_service(create=AsyncMock(return_value=itv)))
    monkeypatch.setattr(
        crud_mod, "AuditService",
        lambda db: SimpleNamespace(log_create=AsyncMock(side_effect=RuntimeError("audit down"))),
    )
    result = await create_OrdresIntervention(data=_data(), db=FakeDb(), current_user=_user())
    assert result is itv


@pytest.mark.asyncio
async def test_create_returns_none_raises_400_not_500(monkeypatch):
    # Regression: this route was missing `except HTTPException: raise`, so its
    # own 400 got caught by `except Exception` below and wrapped into a 500.
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: _fake_service())
    with pytest.raises(HTTPException) as exc_info:
        await create_OrdresIntervention(data=_data(), db=FakeDb(), current_user=_user())
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_create_value_error_raises_400(monkeypatch):
    svc = _fake_service(create=AsyncMock(side_effect=ValueError("bad data")))
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: svc)
    with pytest.raises(HTTPException) as exc_info:
        await create_OrdresIntervention(data=_data(), db=FakeDb(), current_user=_user())
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_create_generic_exception_raises_500(monkeypatch):
    svc = _fake_service(create=AsyncMock(side_effect=RuntimeError("db down")))
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: svc)
    with pytest.raises(HTTPException) as exc_info:
        await create_OrdresIntervention(data=_data(), db=FakeDb(), current_user=_user())
    assert exc_info.value.status_code == 500


# ── create_OrdresInterventions_batch ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_create_success(monkeypatch):
    itv1 = SimpleNamespace(id=1)
    itv2 = SimpleNamespace(id=2)
    svc = _fake_service(create=AsyncMock(side_effect=[itv1, itv2]))
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: svc)
    request = OrdresInterventionBatchCreateRequest(items=[_data(), _data()])
    result = await create_OrdresInterventions_batch(request=request, db=FakeDb(), current_user=_user())
    assert result == [itv1, itv2]


@pytest.mark.asyncio
async def test_batch_create_exception_rolls_back(monkeypatch):
    svc = _fake_service(create=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: svc)
    db = FakeDb()
    request = OrdresInterventionBatchCreateRequest(items=[_data()])
    with pytest.raises(HTTPException) as exc_info:
        await create_OrdresInterventions_batch(request=request, db=db, current_user=_user())
    assert exc_info.value.status_code == 500
    assert db.rolled_back == 1


# ── update_OrdresInterventions_batch ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_update_success(monkeypatch):
    itv = SimpleNamespace(id=1)
    svc = _fake_service(update=AsyncMock(return_value=itv))
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: svc)
    request = OrdresInterventionBatchUpdateRequest(items=[
        {"id": 1, "updates": OrdresInterventionUpdateData(rapport="Done")},
    ])
    result = await update_OrdresInterventions_batch(request=request, db=FakeDb(), current_user=_user())
    assert result == [itv]


@pytest.mark.asyncio
async def test_batch_update_exception_rolls_back(monkeypatch):
    svc = _fake_service(update=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: svc)
    db = FakeDb()
    request = OrdresInterventionBatchUpdateRequest(items=[
        {"id": 1, "updates": OrdresInterventionUpdateData(rapport="X")},
    ])
    with pytest.raises(HTTPException) as exc_info:
        await update_OrdresInterventions_batch(request=request, db=db, current_user=_user())
    assert exc_info.value.status_code == 500
    assert db.rolled_back == 1


# ── update_OrdresIntervention ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_success(monkeypatch):
    old = SimpleNamespace(id=1, rapport="Old")
    new = SimpleNamespace(id=1, rapport="New")
    svc = _fake_service(get_by_id=AsyncMock(return_value=old), update=AsyncMock(return_value=new))
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: svc)
    data = OrdresInterventionUpdateData(rapport="New")
    result = await update_OrdresIntervention(id=1, data=data, db=FakeDb(), current_user=_user())
    assert result is new


@pytest.mark.asyncio
async def test_update_not_found_raises_404(monkeypatch):
    svc = _fake_service(get_by_id=AsyncMock(return_value=None))
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: svc)
    data = OrdresInterventionUpdateData(rapport="New")
    with pytest.raises(HTTPException) as exc_info:
        await update_OrdresIntervention(id=99, data=data, db=FakeDb(), current_user=_user())
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_value_error_raises_400(monkeypatch):
    svc = _fake_service(update=AsyncMock(side_effect=ValueError("bad")))
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: svc)
    data = OrdresInterventionUpdateData(rapport="New")
    with pytest.raises(HTTPException) as exc_info:
        await update_OrdresIntervention(id=1, data=data, db=FakeDb(), current_user=_user())
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_update_generic_exception_raises_500(monkeypatch):
    svc = _fake_service(update=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: svc)
    data = OrdresInterventionUpdateData(rapport="New")
    with pytest.raises(HTTPException) as exc_info:
        await update_OrdresIntervention(id=1, data=data, db=FakeDb(), current_user=_user())
    assert exc_info.value.status_code == 500


# ── delete_OrdresInterventions_batch ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_delete_counts_successes(monkeypatch):
    svc = _fake_service(delete=AsyncMock(side_effect=[True, False]))
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: svc)
    request = OrdresInterventionBatchDeleteRequest(ids=[1, 2])
    result = await delete_OrdresInterventions_batch(request=request, db=FakeDb(), current_user=_user())
    assert result["deleted_count"] == 1


@pytest.mark.asyncio
async def test_batch_delete_exception_rolls_back(monkeypatch):
    svc = _fake_service(delete=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: svc)
    db = FakeDb()
    request = OrdresInterventionBatchDeleteRequest(ids=[1])
    with pytest.raises(HTTPException) as exc_info:
        await delete_OrdresInterventions_batch(request=request, db=db, current_user=_user())
    assert exc_info.value.status_code == 500
    assert db.rolled_back == 1


# ── delete_OrdresIntervention ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_success(monkeypatch):
    svc = _fake_service(delete=AsyncMock(return_value=True))
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: svc)
    result = await delete_OrdresIntervention(id=1, db=FakeDb(), current_user=_user())
    assert result == {"message": "OrdresIntervention deleted successfully", "id": 1}


@pytest.mark.asyncio
async def test_delete_not_found_raises_404(monkeypatch):
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: _fake_service())
    with pytest.raises(HTTPException) as exc_info:
        await delete_OrdresIntervention(id=99, db=FakeDb(), current_user=_user())
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_exception_raises_500(monkeypatch):
    svc = _fake_service(delete=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(crud_mod, "OrdresInterventionService", lambda db: svc)
    with pytest.raises(HTTPException) as exc_info:
        await delete_OrdresIntervention(id=1, db=FakeDb(), current_user=_user())
    assert exc_info.value.status_code == 500
