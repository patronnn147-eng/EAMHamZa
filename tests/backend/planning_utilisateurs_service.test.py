"""Unit tests for app/backend/services/planning_utilisateurs.py (PlanningUtilisateursService).
_apply_filters/_apply_sort come from the shared services/_crud_helpers.py module,
already covered elsewhere — here they're exercised for real (not mocked) since
the calls are cheap, but assertions focus on this service's own logic."""
import pytest

from models.alertes import Alert  # noqa: F401 — registers Alert mapper
from services.planning_utilisateurs import PlanningUtilisateursService


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
    svc = PlanningUtilisateursService(db)
    obj = await svc.create({"planning_id": 1, "utilisateur_id": 2})
    assert obj.utilisateur_id == 2
    assert db.committed == 1
    assert len(db.added) == 1


@pytest.mark.asyncio
async def test_create_rolls_back_on_exception():
    class _FailingDb(FakeDb):
        async def commit(self):
            raise RuntimeError("db down")

    svc = PlanningUtilisateursService(_FailingDb())
    with pytest.raises(RuntimeError):
        await svc.create({"planning_id": 1})
    assert svc.db.rolled_back == 1


# ── get_by_id ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_by_id_found():
    obj = object()
    db = FakeDb([FakeResult(scalar_one_or_none=obj)])
    svc = PlanningUtilisateursService(db)
    assert await svc.get_by_id(1) is obj


@pytest.mark.asyncio
async def test_get_by_id_not_found():
    db = FakeDb([FakeResult(scalar_one_or_none=None)])
    svc = PlanningUtilisateursService(db)
    assert await svc.get_by_id(1) is None


@pytest.mark.asyncio
async def test_get_by_id_propagates_exception():
    class _RaisingDb(FakeDb):
        async def execute(self, *_a, **_k):
            raise RuntimeError("db down")

    svc = PlanningUtilisateursService(_RaisingDb())
    with pytest.raises(RuntimeError):
        await svc.get_by_id(1)


# ── get_list ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_list_returns_items_and_total():
    items = [object(), object()]
    db = FakeDb([FakeResult(scalar_value=2), FakeResult(scalars_list=items)])
    svc = PlanningUtilisateursService(db)
    result = await svc.get_list(skip=0, limit=20)
    assert result["items"] == items
    assert result["total"] == 2
    assert result["skip"] == 0
    assert result["limit"] == 20


@pytest.mark.asyncio
async def test_get_list_applies_query_dict_filter():
    db = FakeDb([FakeResult(scalar_value=1), FakeResult(scalars_list=[object()])])
    svc = PlanningUtilisateursService(db)
    result = await svc.get_list(query_dict={"planning_id": 5})
    assert result["total"] == 1


@pytest.mark.asyncio
async def test_get_list_applies_descending_sort():
    db = FakeDb([FakeResult(scalar_value=0), FakeResult(scalars_list=[])])
    svc = PlanningUtilisateursService(db)
    result = await svc.get_list(sort="-id")
    assert result["items"] == []


@pytest.mark.asyncio
async def test_get_list_propagates_exception():
    class _RaisingDb(FakeDb):
        async def execute(self, *_a, **_k):
            raise RuntimeError("db down")

    svc = PlanningUtilisateursService(_RaisingDb())
    with pytest.raises(RuntimeError):
        await svc.get_list()


# ── update ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_success():
    class Obj:
        id = 1
        utilisateur_id = 2

    db = FakeDb([FakeResult(scalar_one_or_none=Obj())])
    svc = PlanningUtilisateursService(db)
    result = await svc.update(1, {"utilisateur_id": 9})
    assert result.utilisateur_id == 9
    assert db.committed == 1


@pytest.mark.asyncio
async def test_update_not_found_returns_none():
    db = FakeDb([FakeResult(scalar_one_or_none=None)])
    svc = PlanningUtilisateursService(db)
    assert await svc.update(1, {"utilisateur_id": 9}) is None
    assert db.committed == 0


@pytest.mark.asyncio
async def test_update_rolls_back_on_exception():
    class Obj:
        id = 1

    class _FailingDb(FakeDb):
        async def commit(self):
            raise RuntimeError("db down")

    db = _FailingDb([FakeResult(scalar_one_or_none=Obj())])
    svc = PlanningUtilisateursService(db)
    with pytest.raises(RuntimeError):
        await svc.update(1, {"planning_id": 5})
    assert db.rolled_back == 1


# ── delete ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_success():
    class Obj:
        id = 1

    obj = Obj()
    db = FakeDb([FakeResult(scalar_one_or_none=obj)])
    svc = PlanningUtilisateursService(db)
    assert await svc.delete(1) is True
    assert db.deleted == [obj]
    assert db.committed == 1


@pytest.mark.asyncio
async def test_delete_not_found_returns_false():
    db = FakeDb([FakeResult(scalar_one_or_none=None)])
    svc = PlanningUtilisateursService(db)
    assert await svc.delete(1) is False


@pytest.mark.asyncio
async def test_delete_rolls_back_on_exception():
    class Obj:
        id = 1

    class _FailingDb(FakeDb):
        async def commit(self):
            raise RuntimeError("db down")

    db = _FailingDb([FakeResult(scalar_one_or_none=Obj())])
    svc = PlanningUtilisateursService(db)
    with pytest.raises(RuntimeError):
        await svc.delete(1)
    assert db.rolled_back == 1


# ── get_by_field / list_by_field ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_by_field_found():
    obj = object()
    db = FakeDb([FakeResult(scalar_one_or_none=obj)])
    svc = PlanningUtilisateursService(db)
    assert await svc.get_by_field("planning_id", 5) is obj


@pytest.mark.asyncio
async def test_get_by_field_invalid_field_raises_value_error():
    svc = PlanningUtilisateursService(FakeDb())
    with pytest.raises(ValueError):
        await svc.get_by_field("not_a_real_field", 5)


@pytest.mark.asyncio
async def test_list_by_field_returns_matches():
    items = [object()]
    db = FakeDb([FakeResult(scalars_list=items)])
    svc = PlanningUtilisateursService(db)
    result = await svc.list_by_field("planning_id", 5)
    assert result == items


@pytest.mark.asyncio
async def test_list_by_field_invalid_field_raises_value_error():
    svc = PlanningUtilisateursService(FakeDb())
    with pytest.raises(ValueError):
        await svc.list_by_field("not_a_real_field", 5)
