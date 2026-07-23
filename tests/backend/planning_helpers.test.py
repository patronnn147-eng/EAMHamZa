"""Unit tests for app/backend/modules/shared/routes/planning/helpers.py."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from models.alertes import Alert  # noqa: F401 — registers Alert mapper (needed by Utilisateurs relationship)
from models.plannings import PlanningType
from models.utilisateurs import UserRole
from modules.shared.routes.planning.helpers import (
    _enum_val,
    _get_machine_ids,
    _load_users_from_db,
    _load_users_preloaded,
    _recover_chef_users,
    _serialize_planning_for_email,
    _serialize_user,
    _validate_shift_type_fields,
    _validate_user_role,
    get_planning_with_users,
    get_user_by_id,
    send_planning_notifications,
    validate_planning_data,
    verify_admin,
    verify_any_role,
    verify_cheftech,
    verify_cheftech_or_tech,
    verify_chetop_or_cheftech,
)


# ── _serialize_planning_for_email ────────────────────────────────────────────

def test_serialize_planning_for_email_formats_datetime():
    payload = {"id": 1, "date_debut": datetime(2026, 1, 1, 10, 0), "date_fin": None, "type": "SHIFT"}
    result = _serialize_planning_for_email(payload)
    assert result["date_debut"] == "2026-01-01T10:00:00"
    assert result["date_fin"] == ""
    assert result["shift_type"] == ""


def test_serialize_planning_for_email_missing_keys_default_safely():
    result = _serialize_planning_for_email({})
    assert result["identifiant_planning"] == ""
    assert result["zone_travail"] == ""


# ── verify_* role guards ───────────────────────────────────────────────────────

def _user(role):
    return SimpleNamespace(role=role)


def test_verify_admin_allows_admin():
    verify_admin(_user(UserRole.ADMIN))


def test_verify_admin_rejects_others():
    with pytest.raises(HTTPException) as exc_info:
        verify_admin(_user(UserRole.TECHNICIEN))
    assert exc_info.value.status_code == 403


def test_verify_cheftech_allows_cheftech():
    verify_cheftech(_user(UserRole.CHEFTECH))


def test_verify_cheftech_rejects_others():
    with pytest.raises(HTTPException):
        verify_cheftech(_user(UserRole.ADMIN))


def test_verify_chetop_or_cheftech_allows_both():
    verify_chetop_or_cheftech(_user(UserRole.CHETOP))
    verify_chetop_or_cheftech(_user(UserRole.CHEFTECH))


def test_verify_chetop_or_cheftech_rejects_technicien():
    with pytest.raises(HTTPException):
        verify_chetop_or_cheftech(_user(UserRole.TECHNICIEN))


def test_verify_cheftech_or_tech_allows_both():
    verify_cheftech_or_tech(_user(UserRole.CHEFTECH))
    verify_cheftech_or_tech(_user(UserRole.TECHNICIEN))


def test_verify_cheftech_or_tech_rejects_admin():
    with pytest.raises(HTTPException):
        verify_cheftech_or_tech(_user(UserRole.ADMIN))


@pytest.mark.asyncio
async def test_verify_any_role_always_passes():
    await verify_any_role(_user(UserRole.TECHNICIEN))  # must not raise


# ── get_user_by_id ─────────────────────────────────────────────────────────────

class FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def __iter__(self):
        return iter(self._value or [])

    def scalars(self):
        return self

    def all(self):
        return self._value

    def fetchall(self):
        return self._value


class FakeDb:
    def __init__(self, execute_results):
        self._results = list(execute_results)

    async def execute(self, *_a, **_k):
        return self._results.pop(0)


@pytest.mark.asyncio
async def test_get_user_by_id_found():
    user = SimpleNamespace(id=1, nom="Bob")
    db = FakeDb([FakeScalarResult(user)])
    assert await get_user_by_id(db, 1) is user


@pytest.mark.asyncio
async def test_get_user_by_id_not_found():
    db = FakeDb([FakeScalarResult(None)])
    assert await get_user_by_id(db, 1) is None


# ── _enum_val / _serialize_user ───────────────────────────────────────────────

def test_enum_val_none():
    assert _enum_val(None) is None


def test_enum_val_enum_member():
    assert _enum_val(UserRole.ADMIN) == "ADMIN"


def test_enum_val_plain_value():
    assert _enum_val(42) == "42"


def test_serialize_user_full():
    user = SimpleNamespace(id=1, nom="Bob", email="bob@x.com", role=UserRole.TECHNICIEN, shift_type="DAY")
    result = _serialize_user(user)
    assert result == {"id": 1, "nom": "Bob", "email": "bob@x.com", "role": "TECHNICIEN", "shift_type": "DAY"}


def test_serialize_user_without_shift_type_attr():
    user = SimpleNamespace(id=1, nom="Bob", email="bob@x.com", role=UserRole.ADMIN)
    result = _serialize_user(user)
    assert result["shift_type"] is None


# ── _validate_shift_type_fields ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_validate_shift_type_fields_shift_requires_shift_type():
    data = SimpleNamespace(type=PlanningType.SHIFT, shift_type=None, chef_operation_id=1)
    with pytest.raises(HTTPException) as exc_info:
        await _validate_shift_type_fields(data)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_validate_shift_type_fields_shift_requires_chef_operation():
    data = SimpleNamespace(type=PlanningType.SHIFT, shift_type="DAY", chef_operation_id=None)
    with pytest.raises(HTTPException):
        await _validate_shift_type_fields(data)


@pytest.mark.asyncio
async def test_validate_shift_type_fields_non_shift_rejects_shift_type():
    data = SimpleNamespace(type=PlanningType.MAINTENANCE, shift_type="DAY")
    with pytest.raises(HTTPException):
        await _validate_shift_type_fields(data)


@pytest.mark.asyncio
async def test_validate_shift_type_fields_valid_shift_passes():
    data = SimpleNamespace(type=PlanningType.SHIFT, shift_type="DAY", chef_operation_id=1)
    await _validate_shift_type_fields(data)  # must not raise


@pytest.mark.asyncio
async def test_validate_shift_type_fields_valid_non_shift_passes():
    data = SimpleNamespace(type=PlanningType.MAINTENANCE, shift_type=None)
    await _validate_shift_type_fields(data)  # must not raise


# ── _validate_user_role ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_validate_user_role_not_found_raises_404():
    db = FakeDb([FakeScalarResult(None)])
    with pytest.raises(HTTPException) as exc_info:
        await _validate_user_role(db, 1, UserRole.CHETOP, "Chef Operation")
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_validate_user_role_wrong_role_raises_400():
    user = SimpleNamespace(id=1, role=UserRole.TECHNICIEN)
    db = FakeDb([FakeScalarResult(user)])
    with pytest.raises(HTTPException) as exc_info:
        await _validate_user_role(db, 1, UserRole.CHETOP, "Chef Operation")
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_validate_user_role_success():
    user = SimpleNamespace(id=1, role=UserRole.CHETOP)
    db = FakeDb([FakeScalarResult(user)])
    await _validate_user_role(db, 1, UserRole.CHETOP, "Chef Operation")  # must not raise


# ── validate_planning_data ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_validate_planning_data_validates_all_referenced_users():
    chetop = SimpleNamespace(id=1, role=UserRole.CHETOP)
    cheftech = SimpleNamespace(id=2, role=UserRole.CHEFTECH)
    tech = SimpleNamespace(id=3, role=UserRole.TECHNICIEN)
    data = SimpleNamespace(
        type=PlanningType.MAINTENANCE, shift_type=None,
        chef_operation_id=1, chef_technique_id=2, technicien_ids=[3],
    )
    db = FakeDb([FakeScalarResult(chetop), FakeScalarResult(cheftech), FakeScalarResult(tech)])
    await validate_planning_data(db, data)  # must not raise


@pytest.mark.asyncio
async def test_validate_planning_data_no_optional_ids_skips_checks():
    data = SimpleNamespace(type=PlanningType.MAINTENANCE, shift_type=None,
                            chef_operation_id=None, chef_technique_id=None, technicien_ids=[])
    db = FakeDb([])
    await validate_planning_data(db, data)  # must not raise, no DB calls needed


# ── send_planning_notifications ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_planning_notifications_creates_one_per_user(monkeypatch):
    created = []

    class FakeNotificationsService:
        def __init__(self, db):
            pass

        async def create(self, data):
            created.append(data)

    monkeypatch.setattr(
        "modules.shared.routes.planning.helpers.NotificationsService", FakeNotificationsService
    )
    await send_planning_notifications(FakeDb([]), planning_id=1, identifiant_planning="P1", user_ids=[1, 2, 3])
    assert len(created) == 3
    assert created[0]["type"] == "PLANNING_ASSIGNMENT"


@pytest.mark.asyncio
async def test_send_planning_notifications_continues_after_one_failure(monkeypatch):
    calls = []

    class FakeNotificationsService:
        def __init__(self, db):
            pass

        async def create(self, data):
            calls.append(data["utilisateur_id"])
            if data["utilisateur_id"] == 2:
                raise RuntimeError("boom")

    monkeypatch.setattr(
        "modules.shared.routes.planning.helpers.NotificationsService", FakeNotificationsService
    )
    await send_planning_notifications(FakeDb([]), planning_id=1, identifiant_planning="P1", user_ids=[1, 2, 3])
    assert calls == [1, 2, 3]  # user 3 still processed despite user 2's failure


# ── _load_users_preloaded / _load_users_from_db ───────────────────────────────

def test_load_users_preloaded_dedupes_by_id():
    user1 = SimpleNamespace(id=1, nom="A", email="a@x.com", role=UserRole.TECHNICIEN)
    pu1 = SimpleNamespace(utilisateur=user1)
    pu2 = SimpleNamespace(utilisateur=user1)  # duplicate
    planning = SimpleNamespace(PlanningUtilisateurs=[pu1, pu2])
    users, seen = _load_users_preloaded(planning)
    assert len(users) == 1
    assert seen == {1}


def test_load_users_preloaded_skips_missing_user():
    pu = SimpleNamespace(utilisateur=None)
    planning = SimpleNamespace(PlanningUtilisateurs=[pu])
    users, seen = _load_users_preloaded(planning)
    assert users == [] and seen == set()


@pytest.mark.asyncio
async def test_load_users_from_db_dedupes():
    user = SimpleNamespace(id=1, nom="A", email="a@x.com", role=UserRole.TECHNICIEN)
    db = FakeDb([FakeScalarResult([(None, user), (None, user)])])
    users, seen = await _load_users_from_db(db, planning_id=1)
    assert len(users) == 1
    assert seen == {1}


# ── _recover_chef_users ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recover_chef_users_no_chef_ids_returns_empty():
    planning = SimpleNamespace(chef_operation_id=None, chef_technique_id=None)
    result = await _recover_chef_users(FakeDb([]), planning, seen_ids=set())
    assert result == []


@pytest.mark.asyncio
async def test_recover_chef_users_returns_unseen_chefs():
    chef = SimpleNamespace(id=5, nom="Chef", email="c@x.com", role=UserRole.CHEFTECH)
    planning = SimpleNamespace(chef_operation_id=None, chef_technique_id=5)
    db = FakeDb([FakeScalarResult([chef])])
    result = await _recover_chef_users(db, planning, seen_ids=set())
    assert len(result) == 1
    assert result[0]["id"] == 5


@pytest.mark.asyncio
async def test_recover_chef_users_skips_already_seen():
    chef = SimpleNamespace(id=5, nom="Chef", email="c@x.com", role=UserRole.CHEFTECH)
    planning = SimpleNamespace(chef_operation_id=None, chef_technique_id=5)
    db = FakeDb([FakeScalarResult([chef])])
    result = await _recover_chef_users(db, planning, seen_ids={5})
    assert result == []


# ── _get_machine_ids ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_machine_ids_uses_preloaded_relationship():
    planning = SimpleNamespace(PlanningMachines=[SimpleNamespace(machine_id=1), SimpleNamespace(machine_id=2)])
    result = await _get_machine_ids(FakeDb([]), planning)
    assert result == [1, 2]


@pytest.mark.asyncio
async def test_get_machine_ids_falls_back_to_query():
    planning = SimpleNamespace(id=1)  # no PlanningMachines in __dict__
    db = FakeDb([FakeScalarResult([(3,), (4,)])])
    result = await _get_machine_ids(db, planning)
    assert result == [3, 4]


# ── get_planning_with_users ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_planning_with_users_preloaded_path():
    user = SimpleNamespace(id=1, nom="A", email="a@x.com", role=UserRole.TECHNICIEN)
    pu = SimpleNamespace(utilisateur=user)
    planning = SimpleNamespace(
        id=1, identifiant_planning="P1", date_debut=None, date_fin=None,
        type=PlanningType.MAINTENANCE, shift_type=None, planning_statut=None,
        chef_operation_id=None, chef_technique_id=None, zone_travail="Z1", created_at=None,
        PlanningUtilisateurs=[pu], PlanningMachines=[SimpleNamespace(machine_id=1)],
    )
    result = await get_planning_with_users(FakeDb([]), planning)
    assert result["assigned_users"][0]["id"] == 1
    assert result["machine_ids"] == [1]
    assert result["type"] == "MAINTENANCE"


@pytest.mark.asyncio
async def test_get_planning_with_users_recovers_chefs_when_no_assigned_users():
    chef = SimpleNamespace(id=9, nom="Chef", email="c@x.com", role=UserRole.CHEFTECH)
    planning = SimpleNamespace(
        id=1, identifiant_planning="P1", date_debut=None, date_fin=None,
        type=PlanningType.MAINTENANCE, shift_type=None, planning_statut=None,
        chef_operation_id=None, chef_technique_id=9, zone_travail="Z1", created_at=None,
        PlanningUtilisateurs=[],
    )
    db = FakeDb([FakeScalarResult([chef]), FakeScalarResult([(1,)])])
    result = await get_planning_with_users(db, planning)
    assert result["assigned_users"][0]["id"] == 9
