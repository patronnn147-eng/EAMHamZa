"""Unit tests for app/backend/modules/shared/maintenances_planifiees.py.
MaintenancesPlanifieesService is mocked to isolate route-level logic —
same generated-CRUD-template shape as planning_utilisateurs_routes.test.py."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

import modules.shared.maintenances_planifiees as mp_mod
from modules.shared.maintenances_planifiees import (
    MaintenancesPlanifieesBatchCreateRequest,
    MaintenancesPlanifieesBatchDeleteRequest,
    MaintenancesPlanifieesBatchUpdateRequest,
    MaintenancesPlanifieesData,
    MaintenancesPlanifieesUpdateData,
    create_MaintenancesPlanifiees,
    create_MaintenancesPlanifieess_batch,
    delete_MaintenancesPlanifiees,
    delete_MaintenancesPlanifieess_batch,
    get_MaintenancesPlanifiees,
    query_MaintenancesPlanifieess,
    query_MaintenancesPlanifieess_all,
    update_MaintenancesPlanifiees,
    update_MaintenancesPlanifieess_batch,
)


class FakeDb:
    def __init__(self):
        self.rolled_back = 0

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


def _data(**overrides):
    base = dict(date_planifiee=datetime(2026, 1, 1))
    base.update(overrides)
    return MaintenancesPlanifieesData(**base)


# ── query / query_all ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_query_delegates(monkeypatch):
    svc = _fake_service(get_list=AsyncMock(return_value={"items": [], "total": 2, "skip": 0, "limit": 20}))
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: svc)
    result = await query_MaintenancesPlanifieess(query=None, sort=None, skip=0, limit=20, fields=None, db=FakeDb())
    assert result["total"] == 2


@pytest.mark.asyncio
async def test_query_invalid_json_raises_400(monkeypatch):
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: _fake_service())
    with pytest.raises(HTTPException) as exc_info:
        await query_MaintenancesPlanifieess(query="{bad", sort=None, skip=0, limit=20, fields=None, db=FakeDb())
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_query_exception_raises_500(monkeypatch):
    svc = _fake_service(get_list=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: svc)
    with pytest.raises(HTTPException) as exc_info:
        await query_MaintenancesPlanifieess(query=None, sort=None, skip=0, limit=20, fields=None, db=FakeDb())
    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_query_all_variant_delegates(monkeypatch):
    svc = _fake_service()
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: svc)
    result = await query_MaintenancesPlanifieess_all(query=None, sort=None, skip=0, limit=20, fields=None, db=FakeDb())
    assert result["items"] == []


@pytest.mark.asyncio
async def test_query_all_invalid_json_raises_400(monkeypatch):
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: _fake_service())
    with pytest.raises(HTTPException) as exc_info:
        await query_MaintenancesPlanifieess_all(query="{bad", sort=None, skip=0, limit=20, fields=None, db=FakeDb())
    assert exc_info.value.status_code == 400


# ── get ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_found(monkeypatch):
    obj = SimpleNamespace(id=1)
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: _fake_service(get_by_id=AsyncMock(return_value=obj)))
    assert await get_MaintenancesPlanifiees(id=1, fields=None, db=FakeDb()) is obj


@pytest.mark.asyncio
async def test_get_not_found_raises_404(monkeypatch):
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: _fake_service())
    with pytest.raises(HTTPException) as exc_info:
        await get_MaintenancesPlanifiees(id=99, fields=None, db=FakeDb())
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_exception_raises_500(monkeypatch):
    svc = _fake_service(get_by_id=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: svc)
    with pytest.raises(HTTPException) as exc_info:
        await get_MaintenancesPlanifiees(id=1, fields=None, db=FakeDb())
    assert exc_info.value.status_code == 500


# ── create ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_success(monkeypatch):
    obj = SimpleNamespace(id=1)
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: _fake_service(create=AsyncMock(return_value=obj)))
    assert await create_MaintenancesPlanifiees(data=_data(), db=FakeDb()) is obj


@pytest.mark.asyncio
async def test_create_returns_none_raises_400_not_500(monkeypatch):
    # Regression: this route was missing `except HTTPException: raise`.
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: _fake_service())
    with pytest.raises(HTTPException) as exc_info:
        await create_MaintenancesPlanifiees(data=_data(), db=FakeDb())
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_create_value_error_raises_400(monkeypatch):
    svc = _fake_service(create=AsyncMock(side_effect=ValueError("bad")))
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: svc)
    with pytest.raises(HTTPException) as exc_info:
        await create_MaintenancesPlanifiees(data=_data(), db=FakeDb())
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_create_generic_exception_raises_500(monkeypatch):
    svc = _fake_service(create=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: svc)
    with pytest.raises(HTTPException) as exc_info:
        await create_MaintenancesPlanifiees(data=_data(), db=FakeDb())
    assert exc_info.value.status_code == 500


# ── batch create ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_create_success(monkeypatch):
    obj1, obj2 = SimpleNamespace(id=1), SimpleNamespace(id=2)
    svc = _fake_service(create=AsyncMock(side_effect=[obj1, obj2]))
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: svc)
    request = MaintenancesPlanifieesBatchCreateRequest(items=[_data(), _data()])
    result = await create_MaintenancesPlanifieess_batch(request=request, db=FakeDb())
    assert result == [obj1, obj2]


@pytest.mark.asyncio
async def test_batch_create_exception_rolls_back(monkeypatch):
    svc = _fake_service(create=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: svc)
    db = FakeDb()
    request = MaintenancesPlanifieesBatchCreateRequest(items=[_data()])
    with pytest.raises(HTTPException) as exc_info:
        await create_MaintenancesPlanifieess_batch(request=request, db=db)
    assert exc_info.value.status_code == 500
    assert db.rolled_back == 1


# ── batch update ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_update_success(monkeypatch):
    obj = SimpleNamespace(id=1)
    svc = _fake_service(update=AsyncMock(return_value=obj))
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: svc)
    request = MaintenancesPlanifieesBatchUpdateRequest(items=[
        {"id": 1, "updates": MaintenancesPlanifieesUpdateData(description="done")},
    ])
    result = await update_MaintenancesPlanifieess_batch(request=request, db=FakeDb())
    assert result == [obj]


@pytest.mark.asyncio
async def test_batch_update_exception_rolls_back(monkeypatch):
    svc = _fake_service(update=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: svc)
    db = FakeDb()
    request = MaintenancesPlanifieesBatchUpdateRequest(items=[
        {"id": 1, "updates": MaintenancesPlanifieesUpdateData(description="x")},
    ])
    with pytest.raises(HTTPException) as exc_info:
        await update_MaintenancesPlanifieess_batch(request=request, db=db)
    assert exc_info.value.status_code == 500
    assert db.rolled_back == 1


# ── update ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_success(monkeypatch):
    obj = SimpleNamespace(id=1)
    svc = _fake_service(update=AsyncMock(return_value=obj))
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: svc)
    result = await update_MaintenancesPlanifiees(id=1, data=MaintenancesPlanifieesUpdateData(description="done"), db=FakeDb())
    assert result is obj


@pytest.mark.asyncio
async def test_update_not_found_raises_404(monkeypatch):
    svc = _fake_service(update=AsyncMock(return_value=None))
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: svc)
    with pytest.raises(HTTPException) as exc_info:
        await update_MaintenancesPlanifiees(id=99, data=MaintenancesPlanifieesUpdateData(), db=FakeDb())
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_value_error_raises_400(monkeypatch):
    svc = _fake_service(update=AsyncMock(side_effect=ValueError("bad")))
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: svc)
    with pytest.raises(HTTPException) as exc_info:
        await update_MaintenancesPlanifiees(id=1, data=MaintenancesPlanifieesUpdateData(), db=FakeDb())
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_update_generic_exception_raises_500(monkeypatch):
    svc = _fake_service(update=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: svc)
    with pytest.raises(HTTPException) as exc_info:
        await update_MaintenancesPlanifiees(id=1, data=MaintenancesPlanifieesUpdateData(), db=FakeDb())
    assert exc_info.value.status_code == 500


# ── batch delete ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_delete_counts_successes(monkeypatch):
    svc = _fake_service(delete=AsyncMock(side_effect=[True, False]))
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: svc)
    request = MaintenancesPlanifieesBatchDeleteRequest(ids=[1, 2])
    result = await delete_MaintenancesPlanifieess_batch(request=request, db=FakeDb())
    assert result["deleted_count"] == 1


@pytest.mark.asyncio
async def test_batch_delete_exception_rolls_back(monkeypatch):
    svc = _fake_service(delete=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: svc)
    db = FakeDb()
    request = MaintenancesPlanifieesBatchDeleteRequest(ids=[1])
    with pytest.raises(HTTPException) as exc_info:
        await delete_MaintenancesPlanifieess_batch(request=request, db=db)
    assert exc_info.value.status_code == 500
    assert db.rolled_back == 1


# ── delete ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_success(monkeypatch):
    svc = _fake_service(delete=AsyncMock(return_value=True))
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: svc)
    result = await delete_MaintenancesPlanifiees(id=1, db=FakeDb())
    assert result == {"message": "MaintenancesPlanifiees deleted successfully", "id": 1}


@pytest.mark.asyncio
async def test_delete_not_found_raises_404(monkeypatch):
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: _fake_service())
    with pytest.raises(HTTPException) as exc_info:
        await delete_MaintenancesPlanifiees(id=99, db=FakeDb())
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_exception_raises_500(monkeypatch):
    svc = _fake_service(delete=AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(mp_mod, "MaintenancesPlanifieesService", lambda db: svc)
    with pytest.raises(HTTPException) as exc_info:
        await delete_MaintenancesPlanifiees(id=1, db=FakeDb())
    assert exc_info.value.status_code == 500
