"""Unit tests for app/backend/modules/shared/routes/ordres_travail/crud.py.
OrdresTravailService itself is tested separately in ordres_travail_service.test.py —
here it's mocked so these tests focus on route-level logic: JSON query parsing,
HTTP status mapping, batch loops, and non-fatal audit-log failures."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

import modules.shared.routes.ordres_travail.crud as crud_mod
from modules.shared.routes.ordres_travail.crud import (
    OrdresTravailBatchCreateRequest,
    OrdresTravailBatchDeleteRequest,
    OrdresTravailBatchUpdateRequest,
    OrdresTravailData,
    OrdresTravailUpdateData,
    create_OrdresTravail,
    create_OrdresTravails_batch,
    delete_OrdresTravail,
    delete_OrdresTravails_batch,
    get_OrdresTravail,
    query_OrdresTravails,
    query_OrdresTravails_all,
    update_OrdresTravail,
    update_OrdresTravails_batch,
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


# ── query_OrdresTravails / query_OrdresTravails_all ─────────────────────────────

@pytest.mark.asyncio
async def test_query_no_filter_delegates(monkeypatch):
    svc = _fake_service(get_list=AsyncMock(return_value={"items": [], "total": 5, "skip": 0, "limit": 20}))
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: svc)
    result = await query_OrdresTravails(query=None, sort=None, skip=0, limit=20, fields=None, db=FakeDb())
    assert result["total"] == 5
    svc.get_list.assert_awaited_once_with(skip=0, limit=20, query_dict=None, sort=None)


@pytest.mark.asyncio
async def test_query_invalid_json_raises_400(monkeypatch):
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: _fake_service())
    with pytest.raises(HTTPException) as exc_info:
        await query_OrdresTravails(query="{not json", sort=None, skip=0, limit=20, fields=None, db=FakeDb())
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_query_valid_json_parses_query_dict(monkeypatch):
    svc = _fake_service()
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: svc)
    await query_OrdresTravails(query='{"statut": "EN_COURS"}', sort="-id", skip=0, limit=20, fields=None, db=FakeDb())
    svc.get_list.assert_awaited_once_with(skip=0, limit=20, query_dict={"statut": "EN_COURS"}, sort="-id")


@pytest.mark.asyncio
async def test_query_service_exception_raises_500(monkeypatch):
    svc = _fake_service(get_list=AsyncMock(side_effect=RuntimeError("db down")))
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: svc)
    with pytest.raises(HTTPException) as exc_info:
        await query_OrdresTravails(query=None, sort=None, skip=0, limit=20, fields=None, db=FakeDb())
    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_query_all_variant_delegates(monkeypatch):
    svc = _fake_service()
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: svc)
    result = await query_OrdresTravails_all(query=None, sort=None, skip=0, limit=20, fields=None, db=FakeDb())
    assert result["items"] == []
    svc.get_list.assert_awaited_once()


@pytest.mark.asyncio
async def test_query_all_invalid_json_raises_400(monkeypatch):
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: _fake_service())
    with pytest.raises(HTTPException) as exc_info:
        await query_OrdresTravails_all(query="{bad", sort=None, skip=0, limit=20, fields=None, db=FakeDb())
    assert exc_info.value.status_code == 400


# ── get_OrdresTravail ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_found(monkeypatch):
    wo = SimpleNamespace(id=1, titre="Fix pump")
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: _fake_service(get_by_id=AsyncMock(return_value=wo)))
    result = await get_OrdresTravail(id=1, fields=None, db=FakeDb())
    assert result is wo


@pytest.mark.asyncio
async def test_get_not_found_raises_404(monkeypatch):
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: _fake_service())
    with pytest.raises(HTTPException) as exc_info:
        await get_OrdresTravail(id=99, fields=None, db=FakeDb())
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_exception_raises_500(monkeypatch):
    svc = _fake_service(get_by_id=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: svc)
    with pytest.raises(HTTPException) as exc_info:
        await get_OrdresTravail(id=1, fields=None, db=FakeDb())
    assert exc_info.value.status_code == 500


# ── create_OrdresTravail ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_success(monkeypatch):
    wo = SimpleNamespace(id=1, titre="Fix pump")
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: _fake_service(create=AsyncMock(return_value=wo)))
    data = OrdresTravailData(titre="Fix pump", description="desc", machine_id=1)
    result = await create_OrdresTravail(data=data, db=FakeDb(), current_user=_user())
    assert result is wo
    assert data.statut == "EN_ATTENTE"  # route forces this before create


@pytest.mark.asyncio
async def test_create_audit_failure_swallowed(monkeypatch):
    wo = SimpleNamespace(id=1, titre="Fix pump")
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: _fake_service(create=AsyncMock(return_value=wo)))
    monkeypatch.setattr(
        crud_mod, "AuditService",
        lambda db: SimpleNamespace(log_create=AsyncMock(side_effect=RuntimeError("audit down"))),
    )
    data = OrdresTravailData(titre="Fix pump", description="desc", machine_id=1)
    result = await create_OrdresTravail(data=data, db=FakeDb(), current_user=_user())
    assert result is wo  # non-fatal


@pytest.mark.asyncio
async def test_create_returns_none_raises_400(monkeypatch):
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: _fake_service())
    data = OrdresTravailData(titre="Fix pump", description="desc", machine_id=1)
    with pytest.raises(HTTPException) as exc_info:
        await create_OrdresTravail(data=data, db=FakeDb(), current_user=_user())
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_create_value_error_raises_400(monkeypatch):
    svc = _fake_service(create=AsyncMock(side_effect=ValueError("bad data")))
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: svc)
    data = OrdresTravailData(titre="Fix pump", description="desc", machine_id=1)
    with pytest.raises(HTTPException) as exc_info:
        await create_OrdresTravail(data=data, db=FakeDb(), current_user=_user())
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_create_generic_exception_raises_500(monkeypatch):
    svc = _fake_service(create=AsyncMock(side_effect=RuntimeError("db down")))
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: svc)
    data = OrdresTravailData(titre="Fix pump", description="desc", machine_id=1)
    with pytest.raises(HTTPException) as exc_info:
        await create_OrdresTravail(data=data, db=FakeDb(), current_user=_user())
    assert exc_info.value.status_code == 500


# ── create_OrdresTravails_batch ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_create_success(monkeypatch):
    wo1 = SimpleNamespace(id=1, titre="A")
    wo2 = SimpleNamespace(id=2, titre="B")
    svc = _fake_service(create=AsyncMock(side_effect=[wo1, wo2]))
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: svc)
    request = OrdresTravailBatchCreateRequest(items=[
        OrdresTravailData(titre="A", description="d", machine_id=1),
        OrdresTravailData(titre="B", description="d", machine_id=2),
    ])
    result = await create_OrdresTravails_batch(request=request, db=FakeDb(), current_user=_user())
    assert result == [wo1, wo2]


@pytest.mark.asyncio
async def test_batch_create_exception_rolls_back(monkeypatch):
    svc = _fake_service(create=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: svc)
    db = FakeDb()
    request = OrdresTravailBatchCreateRequest(items=[
        OrdresTravailData(titre="A", description="d", machine_id=1),
    ])
    with pytest.raises(HTTPException) as exc_info:
        await create_OrdresTravails_batch(request=request, db=db, current_user=_user())
    assert exc_info.value.status_code == 500
    assert db.rolled_back == 1


# ── update_OrdresTravails_batch ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_update_success(monkeypatch):
    wo = SimpleNamespace(id=1, titre="Updated")
    svc = _fake_service(update=AsyncMock(return_value=wo))
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: svc)
    request = OrdresTravailBatchUpdateRequest(items=[
        {"id": 1, "updates": OrdresTravailUpdateData(titre="Updated")},
    ])
    result = await update_OrdresTravails_batch(request=request, db=FakeDb(), current_user=_user())
    assert result == [wo]


@pytest.mark.asyncio
async def test_batch_update_exception_rolls_back(monkeypatch):
    svc = _fake_service(update=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: svc)
    db = FakeDb()
    request = OrdresTravailBatchUpdateRequest(items=[
        {"id": 1, "updates": OrdresTravailUpdateData(titre="X")},
    ])
    with pytest.raises(HTTPException) as exc_info:
        await update_OrdresTravails_batch(request=request, db=db, current_user=_user())
    assert exc_info.value.status_code == 500
    assert db.rolled_back == 1


# ── update_OrdresTravail ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_success(monkeypatch):
    old = SimpleNamespace(id=1, titre="Old")
    new = SimpleNamespace(id=1, titre="New")
    svc = _fake_service(get_by_id=AsyncMock(return_value=old), update=AsyncMock(return_value=new))
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: svc)
    data = OrdresTravailUpdateData(titre="New")
    result = await update_OrdresTravail(id=1, data=data, db=FakeDb(), current_user=_user())
    assert result is new


@pytest.mark.asyncio
async def test_update_not_found_raises_404(monkeypatch):
    svc = _fake_service(get_by_id=AsyncMock(return_value=None))
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: svc)
    data = OrdresTravailUpdateData(titre="New")
    with pytest.raises(HTTPException) as exc_info:
        await update_OrdresTravail(id=99, data=data, db=FakeDb(), current_user=_user())
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_value_error_raises_400(monkeypatch):
    svc = _fake_service(update=AsyncMock(side_effect=ValueError("bad")))
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: svc)
    data = OrdresTravailUpdateData(titre="New")
    with pytest.raises(HTTPException) as exc_info:
        await update_OrdresTravail(id=1, data=data, db=FakeDb(), current_user=_user())
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_update_generic_exception_raises_500(monkeypatch):
    svc = _fake_service(update=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: svc)
    data = OrdresTravailUpdateData(titre="New")
    with pytest.raises(HTTPException) as exc_info:
        await update_OrdresTravail(id=1, data=data, db=FakeDb(), current_user=_user())
    assert exc_info.value.status_code == 500


# ── delete_OrdresTravails_batch ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_delete_counts_successes(monkeypatch):
    svc = _fake_service(delete=AsyncMock(side_effect=[True, False, True]))
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: svc)
    request = OrdresTravailBatchDeleteRequest(ids=[1, 2, 3])
    result = await delete_OrdresTravails_batch(request=request, db=FakeDb(), current_user=_user())
    assert result["deleted_count"] == 2


@pytest.mark.asyncio
async def test_batch_delete_exception_rolls_back(monkeypatch):
    svc = _fake_service(delete=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: svc)
    db = FakeDb()
    request = OrdresTravailBatchDeleteRequest(ids=[1])
    with pytest.raises(HTTPException) as exc_info:
        await delete_OrdresTravails_batch(request=request, db=db, current_user=_user())
    assert exc_info.value.status_code == 500
    assert db.rolled_back == 1


# ── delete_OrdresTravail ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_success(monkeypatch):
    svc = _fake_service(delete=AsyncMock(return_value=True))
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: svc)
    result = await delete_OrdresTravail(id=1, db=FakeDb(), current_user=_user())
    assert result == {"message": "OrdresTravail deleted successfully", "id": 1}


@pytest.mark.asyncio
async def test_delete_not_found_raises_404(monkeypatch):
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: _fake_service())
    with pytest.raises(HTTPException) as exc_info:
        await delete_OrdresTravail(id=99, db=FakeDb(), current_user=_user())
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_exception_raises_500(monkeypatch):
    svc = _fake_service(delete=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(crud_mod, "OrdresTravailService", lambda db: svc)
    with pytest.raises(HTTPException) as exc_info:
        await delete_OrdresTravail(id=1, db=FakeDb(), current_user=_user())
    assert exc_info.value.status_code == 500
