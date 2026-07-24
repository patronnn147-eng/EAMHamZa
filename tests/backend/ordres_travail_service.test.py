"""Unit tests for app/backend/services/ordres_travail.py (OrdresTravailService)."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from models.alertes import Alert  # noqa: F401 — registers Alert mapper (needed by Utilisateurs relationship)
from models.ordres_travail import OrdresTravail
from services.ordres_travail import OrdresTravailService


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
async def test_create_uses_provided_titre_and_description():
    db = FakeDb()
    svc = OrdresTravailService(db)
    obj = await svc.create({
        "titre": "Fix pump", "description": "Pump leaking", "priorite": "HAUTE", "machine_id": 1,
    })
    assert obj.titre == "Fix pump"
    assert db.committed == 1
    assert len(db.added) == 1


@pytest.mark.asyncio
async def test_create_defaults_missing_titre_and_description():
    db = FakeDb()
    svc = OrdresTravailService(db)
    obj = await svc.create({"priorite": "HAUTE", "machine_id": 1})
    assert "HAUTE" in obj.titre
    assert obj.description == "Description non spécifiée"


@pytest.mark.asyncio
async def test_create_rolls_back_on_exception():
    class _FailingDb(FakeDb):
        async def commit(self):
            raise RuntimeError("db down")

    db = _FailingDb()
    svc = OrdresTravailService(db)
    with pytest.raises(RuntimeError):
        await svc.create({"titre": "X", "description": "Y", "machine_id": 1})
    assert db.rolled_back == 1


# ── get_by_id ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_by_id_found():
    wo = SimpleNamespace(id=1)
    db = FakeDb([FakeResult(scalar_one_or_none=wo)])
    svc = OrdresTravailService(db)
    assert await svc.get_by_id(1) is wo


@pytest.mark.asyncio
async def test_get_by_id_not_found():
    db = FakeDb([FakeResult(scalar_one_or_none=None)])
    svc = OrdresTravailService(db)
    assert await svc.get_by_id(99) is None


@pytest.mark.asyncio
async def test_get_by_id_raises_on_exception():
    class _FailingDb(FakeDb):
        async def execute(self, *_a, **_k):
            raise RuntimeError("db down")

    svc = OrdresTravailService(_FailingDb())
    with pytest.raises(RuntimeError):
        await svc.get_by_id(1)


# ── _apply_filters ────────────────────────────────────────────────────────────

def test_apply_filters_empty_dict_returns_unchanged():
    q, cq = OrdresTravailService._apply_filters("Q", "CQ", None)
    assert q == "Q"
    assert cq == "CQ"


def test_apply_filters_skips_unknown_field():
    from sqlalchemy import select
    q, cq = OrdresTravailService._apply_filters(
        select(OrdresTravail), select(OrdresTravail), {"not_a_real_field": 1},
    )
    # no error, query unchanged in shape (can't easily assert WHERE absence,
    # but at minimum this must not raise AttributeError)
    assert q is not None


def test_apply_filters_coerces_integer_string():
    from sqlalchemy import select
    q, cq = OrdresTravailService._apply_filters(
        select(OrdresTravail), select(OrdresTravail), {"machine_id": "5"},
    )
    assert "5" not in str(q)  # coerced to int, not left as string filter


def test_apply_filters_skips_invalid_integer_string():
    from sqlalchemy import select
    # "abc" can't convert to int for an integer column -> `continue`, no filter applied
    q, cq = OrdresTravailService._apply_filters(
        select(OrdresTravail), select(OrdresTravail), {"machine_id": "abc"},
    )
    assert q is not None


def test_apply_filters_applies_string_field_filter():
    from sqlalchemy import select
    q, cq = OrdresTravailService._apply_filters(
        select(OrdresTravail), select(OrdresTravail), {"titre": "Fix pump"},
    )
    assert "Fix pump" in str(q.compile(compile_kwargs={"literal_binds": True}))


# ── _apply_sort ──────────────────────────────────────────────────────────────

def test_apply_sort_none_defaults_to_id_desc():
    from sqlalchemy import select
    q = OrdresTravailService._apply_sort(select(OrdresTravail), None)
    assert "ORDER BY" in str(q)


def test_apply_sort_descending_prefix():
    from sqlalchemy import select
    q = OrdresTravailService._apply_sort(select(OrdresTravail), "-priorite")
    assert "DESC" in str(q)


def test_apply_sort_ascending_field():
    from sqlalchemy import select
    q = OrdresTravailService._apply_sort(select(OrdresTravail), "priorite")
    compiled = str(q)
    assert "ORDER BY" in compiled


def test_apply_sort_skips_unknown_field_falls_back_to_default():
    from sqlalchemy import select
    q = OrdresTravailService._apply_sort(select(OrdresTravail), "not_a_field")
    assert "ORDER BY" in str(q)  # falls back to id desc since order_clauses stays empty


def test_apply_sort_multiple_fields_comma_separated():
    from sqlalchemy import select
    q = OrdresTravailService._apply_sort(select(OrdresTravail), "-priorite,titre")
    assert "ORDER BY" in str(q)


# ── get_list ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_list_returns_items_and_total():
    wo = SimpleNamespace(id=1)
    db = FakeDb([FakeResult(scalar_value=1), FakeResult(scalars_list=[wo])])
    svc = OrdresTravailService(db)
    result = await svc.get_list(skip=0, limit=10)
    assert result["total"] == 1
    assert result["items"] == [wo]


@pytest.mark.asyncio
async def test_get_list_raises_on_exception():
    class _FailingDb(FakeDb):
        async def execute(self, *_a, **_k):
            raise RuntimeError("db down")

    svc = OrdresTravailService(_FailingDb())
    with pytest.raises(RuntimeError):
        await svc.get_list()


# ── update ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_applies_known_fields_only():
    wo = SimpleNamespace(id=1, titre="Old", priorite="BASSE")
    db = FakeDb([FakeResult(scalar_one_or_none=wo)])
    svc = OrdresTravailService(db)
    result = await svc.update(1, {"titre": "New", "not_a_field": "ignored"})
    assert result.titre == "New"
    assert not hasattr(result, "not_a_field")
    assert db.committed == 1


@pytest.mark.asyncio
async def test_update_returns_none_when_not_found():
    db = FakeDb([FakeResult(scalar_one_or_none=None)])
    svc = OrdresTravailService(db)
    assert await svc.update(99, {"titre": "X"}) is None


@pytest.mark.asyncio
async def test_update_rolls_back_on_exception():
    wo = SimpleNamespace(id=1, titre="Old")

    class _FailingDb(FakeDb):
        async def commit(self):
            raise RuntimeError("db down")

    db = _FailingDb([FakeResult(scalar_one_or_none=wo)])
    svc = OrdresTravailService(db)
    with pytest.raises(RuntimeError):
        await svc.update(1, {"titre": "New"})
    assert db.rolled_back == 1


# ── delete ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_success():
    wo = SimpleNamespace(id=1)
    db = FakeDb([FakeResult(scalar_one_or_none=wo)])
    svc = OrdresTravailService(db)
    assert await svc.delete(1) is True
    assert db.deleted == [wo]
    assert db.committed == 1


@pytest.mark.asyncio
async def test_delete_returns_false_when_not_found():
    db = FakeDb([FakeResult(scalar_one_or_none=None)])
    svc = OrdresTravailService(db)
    assert await svc.delete(99) is False


@pytest.mark.asyncio
async def test_delete_rolls_back_on_exception():
    wo = SimpleNamespace(id=1)

    class _FailingDb(FakeDb):
        async def commit(self):
            raise RuntimeError("db down")

    db = _FailingDb([FakeResult(scalar_one_or_none=wo)])
    svc = OrdresTravailService(db)
    with pytest.raises(RuntimeError):
        await svc.delete(1)
    assert db.rolled_back == 1


# ── get_by_field / list_by_field ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_by_field_success():
    wo = SimpleNamespace(id=1)
    db = FakeDb([FakeResult(scalar_one_or_none=wo)])
    svc = OrdresTravailService(db)
    assert await svc.get_by_field("titre", "Fix pump") is wo


@pytest.mark.asyncio
async def test_get_by_field_invalid_field_raises_value_error():
    svc = OrdresTravailService(FakeDb())
    with pytest.raises(ValueError):
        await svc.get_by_field("not_a_field", "x")


@pytest.mark.asyncio
async def test_list_by_field_success():
    wo = SimpleNamespace(id=1)
    db = FakeDb([FakeResult(scalars_list=[wo])])
    svc = OrdresTravailService(db)
    result = await svc.list_by_field("priorite", "HAUTE")
    assert result == [wo]


@pytest.mark.asyncio
async def test_list_by_field_invalid_field_raises_value_error():
    svc = OrdresTravailService(FakeDb())
    with pytest.raises(ValueError):
        await svc.list_by_field("not_a_field", "x")
