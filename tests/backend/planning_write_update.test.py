"""Unit tests for the pure/easily-faked helpers in
app/backend/modules/shared/routes/planning/write.py and update.py."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from models.alertes import Alert  # noqa: F401 — registers Alert mapper (needed by Utilisateurs relationship)
from models.plannings import PlanningStatut, PlanningType
from modules.shared.routes.planning.update import (
    _build_update_dict,
    _compute_user_id_set,
    _rebuild_user_assignments,
    _update_machine_assignments,
    get_users_by_role,
)
from modules.shared.routes.planning.write import (
    _add_machines_to_planning,
    _collect_user_ids,
    _resolve_planning_statut,
    _validate_shift_compatibility,
)


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class FakeDb:
    def __init__(self, execute_results=None):
        self._results = list(execute_results or [])
        self.added = []
        self.committed = 0

    async def execute(self, *_a, **_k):
        return self._results.pop(0)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed += 1


# ── write.py: _resolve_planning_statut ────────────────────────────────────────

def test_resolve_planning_statut_none_defaults_to_draft():
    assert _resolve_planning_statut(None) == PlanningStatut.DRAFT


def test_resolve_planning_statut_valid_value():
    assert _resolve_planning_statut("APPROVED") == PlanningStatut.APPROVED


def test_resolve_planning_statut_invalid_value_falls_back_to_draft():
    assert _resolve_planning_statut("NOT_A_STATUS") == PlanningStatut.DRAFT


# ── write.py: _collect_user_ids ───────────────────────────────────────────────

def test_collect_user_ids_aggregates_and_dedupes():
    data = SimpleNamespace(chef_operation_id=1, chef_technique_id=2, technicien_ids=[2, 3])
    result = set(_collect_user_ids(data))
    assert result == {1, 2, 3}


def test_collect_user_ids_all_none():
    data = SimpleNamespace(chef_operation_id=None, chef_technique_id=None, technicien_ids=None)
    assert _collect_user_ids(data) == []


# ── write.py: _add_machines_to_planning ───────────────────────────────────────

@pytest.mark.asyncio
async def test_add_machines_to_planning_dedupes_and_sorts():
    db = FakeDb()
    result = await _add_machines_to_planning(db, planning_id=1, machine_ids=[3, 1, 3, 2], now=None)
    assert result == [1, 2, 3]
    assert len(db.added) == 3
    assert db.committed == 1


# ── write.py: _validate_shift_compatibility ───────────────────────────────────

@pytest.mark.asyncio
async def test_validate_shift_compatibility_noop_for_non_shift_planning():
    db = FakeDb()
    await _validate_shift_compatibility(db, [1, 2], "DAY", PlanningType.MAINTENANCE.value)
    # no db.execute call needed - would raise IndexError from empty FakeDb if it tried


@pytest.mark.asyncio
async def test_validate_shift_compatibility_noop_when_no_users():
    db = FakeDb()
    await _validate_shift_compatibility(db, [], "DAY", PlanningType.SHIFT.value)


@pytest.mark.asyncio
async def test_validate_shift_compatibility_raises_on_mismatch():
    db = FakeDb([FakeResult([(5,)])])
    with pytest.raises(HTTPException) as exc_info:
        await _validate_shift_compatibility(db, [1, 5], "DAY", PlanningType.SHIFT.value)
    assert exc_info.value.status_code == 400
    assert "5" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_shift_compatibility_passes_when_all_match():
    db = FakeDb([FakeResult([])])
    await _validate_shift_compatibility(db, [1, 2], "DAY", PlanningType.SHIFT.value)


# ── update.py: _build_update_dict ─────────────────────────────────────────────

def test_build_update_dict_includes_only_non_none_fields():
    data = SimpleNamespace(
        identifiant_planning="P1", date_debut=None, date_fin=None, type=None,
        shift_type=None, chef_operation_id=5, chef_technique_id=None, zone_travail=None,
    )
    result = _build_update_dict(data)
    assert result == {"identifiant_planning": "P1", "chef_operation_id": 5}


def test_build_update_dict_all_none_returns_empty():
    data = SimpleNamespace(
        identifiant_planning=None, date_debut=None, date_fin=None, type=None,
        shift_type=None, chef_operation_id=None, chef_technique_id=None, zone_travail=None,
    )
    assert _build_update_dict(data) == {}


# ── update.py: _compute_user_id_set ───────────────────────────────────────────

def test_compute_user_id_set_uses_new_chef_ids_when_provided():
    data = SimpleNamespace(chef_operation_id=10, chef_technique_id=20, technicien_ids=[30])
    result = _compute_user_id_set(data, original_chef_op=1, original_chef_tech=2, existing_tech_ids={99})
    assert result == {10, 20, 30}


def test_compute_user_id_set_keeps_original_chefs_when_not_overridden():
    data = SimpleNamespace(chef_operation_id=None, chef_technique_id=None, technicien_ids=None)
    result = _compute_user_id_set(data, original_chef_op=1, original_chef_tech=2, existing_tech_ids={99})
    assert result == {1, 2, 99}


def test_compute_user_id_set_no_chefs_at_all():
    data = SimpleNamespace(chef_operation_id=None, chef_technique_id=None, technicien_ids=None)
    result = _compute_user_id_set(data, original_chef_op=None, original_chef_tech=None, existing_tech_ids=set())
    assert result == set()


# ── update.py: _rebuild_user_assignments ──────────────────────────────────────

@pytest.mark.asyncio
async def test_rebuild_user_assignments_preserves_existing_techs():
    data = SimpleNamespace(chef_operation_id=None, chef_technique_id=None, technicien_ids=None)
    db = FakeDb([FakeResult([(1,), (2,), (3,)]), FakeResult(None)])  # select, then delete
    result = await _rebuild_user_assignments(db, planning_id=1, data=data, original_chef_op=1, original_chef_tech=None)
    assert set(result) == {1, 2, 3}
    assert db.committed == 1


@pytest.mark.asyncio
async def test_rebuild_user_assignments_overrides_technicians():
    data = SimpleNamespace(chef_operation_id=None, chef_technique_id=None, technicien_ids=[7, 8])
    db = FakeDb([FakeResult([(1,), (2,)]), FakeResult(None)])  # select, then delete
    result = await _rebuild_user_assignments(db, planning_id=1, data=data, original_chef_op=1, original_chef_tech=None)
    assert set(result) == {1, 7, 8}


# ── update.py: _update_machine_assignments ────────────────────────────────────

@pytest.mark.asyncio
async def test_update_machine_assignments_replaces_when_provided():
    data = SimpleNamespace(machine_ids=[3, 1, 1])
    db = FakeDb([FakeResult([])])
    result = await _update_machine_assignments(db, planning_id=1, data=data, existing_machine_ids=[9])
    assert result == [1, 3]
    assert db.committed == 1


@pytest.mark.asyncio
async def test_update_machine_assignments_keeps_existing_when_empty():
    data = SimpleNamespace(machine_ids=[])
    db = FakeDb([])
    result = await _update_machine_assignments(db, planning_id=1, data=data, existing_machine_ids=[9])
    assert result == [9]


@pytest.mark.asyncio
async def test_update_machine_assignments_keeps_existing_when_none():
    data = SimpleNamespace(machine_ids=None)
    db = FakeDb([])
    result = await _update_machine_assignments(db, planning_id=1, data=data, existing_machine_ids=[9])
    assert result == [9]


# ── update.py: get_users_by_role ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_users_by_role_rejects_non_admin():
    from models.utilisateurs import UserRole
    with pytest.raises(HTTPException) as exc_info:
        await get_users_by_role(
            UserRole.TECHNICIEN, current_user=SimpleNamespace(role=UserRole.TECHNICIEN), db=FakeDb([])
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_users_by_role_returns_serialized_users():
    from models.utilisateurs import UserRole

    user = SimpleNamespace(id=1, nom="Bob", email="bob@x.com", role=UserRole.TECHNICIEN, shift_type=None)
    db = FakeDb([FakeResult([user])])
    result = await get_users_by_role(
        UserRole.TECHNICIEN, current_user=SimpleNamespace(role=UserRole.ADMIN), db=db
    )
    assert len(result) == 1
    assert result[0].nom == "Bob"
    assert result[0].shift_type is None
