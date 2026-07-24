"""Unit tests for app/backend/services/ordres_intervention.py (OrdresInterventionService).
_apply_filters/_apply_sort come from the shared services/_crud_helpers.py module,
already covered elsewhere — here they're exercised for real (not mocked) since
the calls are cheap, but assertions focus on this service's own logic."""
from types import SimpleNamespace

import pytest

from models.alertes import Alert  # noqa: F401 — registers Alert mapper (needed by Utilisateurs relationship)
from services.ordres_intervention import OrdresInterventionService


class FakeResult:
    def __init__(self, scalar_one_or_none=None, scalar_value=None, scalars_list=None):
        self._soo = scalar_one_or_none
        self._scalar_value = scalar_value
        self._scalars_list = scalars_list

    def scalar_one_or_none(self):
        return self._soo

    def scalar(self):
        return self._scalar_value

    def scalars(self):
        return self

    def all(self):
        return self._scalars_list or []


class FakeDb:
    def __init__(self, execute_results=None):
        self._results = list(execute_results or [])
        self.added = []
        self.committed = 0
        self.rolled_back = 0
        self.refreshed = 0
        self.deleted = []

    async def execute(self, *_a, **_k):
        return self._results.pop(0)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed += 1

    async def rollback(self):
        self.rolled_back += 1

    async def refresh(self, obj):
        self.refreshed += 1

    async def delete(self, obj):
        self.deleted.append(obj)


# ── create ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_success():
    db = FakeDb()
    svc = OrdresInterventionService(db)
    obj = await svc.create({"date_intervention": "2026-01-01", "machine_id": 1})
    assert obj.machine_id == 1
    assert db.committed == 1
    assert len(db.added) == 1


@pytest.mark.asyncio
async def test_create_rolls_back_on_exception():
    class _FailingDb(FakeDb):
        async def commit(self):
            raise RuntimeError("db down")

    svc = OrdresInterventionService(_FailingDb())
    with pytest.raises(RuntimeError):
        await svc.create({"date_intervention": "2026-01-01"})
    assert svc.db.rolled_back == 1


# ── get_by_id ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_by_id_found():
    itv = SimpleNamespace(id=1)
    db = FakeDb([FakeResult(scalar_one_or_none=itv)])
    svc = OrdresInterventionService(db)
    assert await svc.get_by_id(1) is itv


@pytest.mark.asyncio
async def test_get_by_id_not_found():
    db = FakeDb([FakeResult(scalar_one_or_none=None)])
    svc = OrdresInterventionService(db)
    assert await svc.get_by_id(99) is None


@pytest.mark.asyncio
async def test_get_by_id_raises_on_exception():
    class _FailingDb(FakeDb):
        async def execute(self, *_a, **_k):
            raise RuntimeError("db down")

    svc = OrdresInterventionService(_FailingDb())
    with pytest.raises(RuntimeError):
        await svc.get_by_id(1)


# ── get_list ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_list_returns_items_and_total():
    itv = SimpleNamespace(id=1)
    db = FakeDb([FakeResult(scalar_value=1), FakeResult(scalars_list=[itv])])
    svc = OrdresInterventionService(db)
    result = await svc.get_list(skip=0, limit=10)
    assert result["total"] == 1
    assert result["items"] == [itv]


@pytest.mark.asyncio
async def test_get_list_with_filters_and_sort():
    db = FakeDb([FakeResult(scalar_value=0), FakeResult(scalars_list=[])])
    svc = OrdresInterventionService(db)
    result = await svc.get_list(query_dict={"machine_id": 1}, sort="-id")
    assert result["items"] == []


@pytest.mark.asyncio
async def test_get_list_raises_on_exception():
    class _FailingDb(FakeDb):
        async def execute(self, *_a, **_k):
            raise RuntimeError("db down")

    svc = OrdresInterventionService(_FailingDb())
    with pytest.raises(RuntimeError):
        await svc.get_list()


# ── update ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_applies_known_fields_only():
    itv = SimpleNamespace(id=1, rapport="Old")
    db = FakeDb([FakeResult(scalar_one_or_none=itv)])
    svc = OrdresInterventionService(db)
    result = await svc.update(1, {"rapport": "New", "not_a_field": "ignored"})
    assert result.rapport == "New"
    assert not hasattr(result, "not_a_field")
    assert db.committed == 1


@pytest.mark.asyncio
async def test_update_returns_none_when_not_found():
    db = FakeDb([FakeResult(scalar_one_or_none=None)])
    svc = OrdresInterventionService(db)
    assert await svc.update(99, {"rapport": "X"}) is None


@pytest.mark.asyncio
async def test_update_rolls_back_on_exception():
    itv = SimpleNamespace(id=1, rapport="Old")

    class _FailingDb(FakeDb):
        async def commit(self):
            raise RuntimeError("db down")

    db = _FailingDb([FakeResult(scalar_one_or_none=itv)])
    svc = OrdresInterventionService(db)
    with pytest.raises(RuntimeError):
        await svc.update(1, {"rapport": "New"})
    assert db.rolled_back == 1


# ── delete ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_success():
    itv = SimpleNamespace(id=1)
    db = FakeDb([FakeResult(scalar_one_or_none=itv)])
    svc = OrdresInterventionService(db)
    assert await svc.delete(1) is True
    assert db.deleted == [itv]
    assert db.committed == 1


@pytest.mark.asyncio
async def test_delete_returns_false_when_not_found():
    db = FakeDb([FakeResult(scalar_one_or_none=None)])
    svc = OrdresInterventionService(db)
    assert await svc.delete(99) is False


@pytest.mark.asyncio
async def test_delete_rolls_back_on_exception():
    itv = SimpleNamespace(id=1)

    class _FailingDb(FakeDb):
        async def commit(self):
            raise RuntimeError("db down")

    db = _FailingDb([FakeResult(scalar_one_or_none=itv)])
    svc = OrdresInterventionService(db)
    with pytest.raises(RuntimeError):
        await svc.delete(1)
    assert db.rolled_back == 1


# ── get_by_field / list_by_field ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_by_field_success():
    itv = SimpleNamespace(id=1)
    db = FakeDb([FakeResult(scalar_one_or_none=itv)])
    svc = OrdresInterventionService(db)
    assert await svc.get_by_field("machine_id", 1) is itv


@pytest.mark.asyncio
async def test_get_by_field_invalid_field_raises_value_error():
    svc = OrdresInterventionService(FakeDb())
    with pytest.raises(ValueError):
        await svc.get_by_field("not_a_field", "x")


@pytest.mark.asyncio
async def test_list_by_field_success():
    itv = SimpleNamespace(id=1)
    db = FakeDb([FakeResult(scalars_list=[itv])])
    svc = OrdresInterventionService(db)
    result = await svc.list_by_field("machine_id", 1)
    assert result == [itv]


@pytest.mark.asyncio
async def test_list_by_field_invalid_field_raises_value_error():
    svc = OrdresInterventionService(FakeDb())
    with pytest.raises(ValueError):
        await svc.list_by_field("not_a_field", "x")
