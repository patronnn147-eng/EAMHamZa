"""Unit tests for create_intervention_from_planning in
app/backend/modules/shared/routes/intervention_workflow.py."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from models.alertes import Alert  # noqa: F401 — registers Alert mapper (needed by Utilisateurs relationship)
from models.utilisateurs import UserRole
import modules.shared.routes.intervention_workflow as iw_mod
from modules.shared.routes.intervention_workflow import create_intervention_from_planning


class FakeDb:
    def __init__(self, scalars=None):
        self._scalars = list(scalars or [])
        self.added = []
        self.committed = 0

    async def scalar(self, *_a, **_k):
        return self._scalars.pop(0)

    def add(self, obj):
        self.added.append(obj)
        obj.id = 100

    async def commit(self):
        self.committed += 1

    async def refresh(self, obj):
        pass


def _user(role, id=1, nom="Bob"):
    return SimpleNamespace(id=id, nom=nom, role=role)


def _planning(statut="APPROVED", chef_operation_id=None, chef_technique_id=None):
    return SimpleNamespace(
        id=1, planning_statut=statut,
        chef_operation_id=chef_operation_id, chef_technique_id=chef_technique_id,
    )


def _machine():
    return SimpleNamespace(id=1)


@pytest.fixture(autouse=True)
def _stub_audit(monkeypatch):
    monkeypatch.setattr(iw_mod, "AuditService", lambda db: SimpleNamespace(log_create=AsyncMock()))


@pytest.mark.asyncio
async def test_planning_not_found_raises_404():
    db = FakeDb(scalars=[None])
    with pytest.raises(HTTPException) as exc_info:
        await create_intervention_from_planning(
            planning_id=99, machine_id=1, problem_description="noisy",
            current_user=_user(UserRole.ADMIN), db=db,
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_planning_not_approved_raises_400():
    db = FakeDb(scalars=[_planning(statut="DRAFT")])
    with pytest.raises(HTTPException) as exc_info:
        await create_intervention_from_planning(
            planning_id=1, machine_id=1, problem_description="noisy",
            current_user=_user(UserRole.ADMIN), db=db,
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_machine_not_found_raises_404():
    db = FakeDb(scalars=[_planning(), None])
    with pytest.raises(HTTPException) as exc_info:
        await create_intervention_from_planning(
            planning_id=1, machine_id=99, problem_description="noisy",
            current_user=_user(UserRole.ADMIN), db=db,
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_chetop_owner_has_permission_and_succeeds():
    # Regression: real code compared user_role to the nonexistent
    # UserRole.CHEFOP (typo for CHETOP), raising an unhandled AttributeError
    # for every CHETOP caller before this permission check ever completed.
    db = FakeDb(scalars=[_planning(chef_operation_id=1), _machine()])
    result = await create_intervention_from_planning(
        planning_id=1, machine_id=1, problem_description="noisy",
        current_user=_user(UserRole.CHETOP, id=1), db=db,
    )
    assert result.id == 100
    assert db.committed == 1


@pytest.mark.asyncio
async def test_chetop_non_owner_rejected():
    db = FakeDb(scalars=[_planning(chef_operation_id=999), _machine()])
    with pytest.raises(HTTPException) as exc_info:
        await create_intervention_from_planning(
            planning_id=1, machine_id=1, problem_description="noisy",
            current_user=_user(UserRole.CHETOP, id=1), db=db,
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_cheftech_owner_has_permission():
    db = FakeDb(scalars=[_planning(chef_technique_id=1), _machine()])
    result = await create_intervention_from_planning(
        planning_id=1, machine_id=1, problem_description="noisy",
        current_user=_user(UserRole.CHEFTECH, id=1), db=db,
    )
    assert result.id == 100


@pytest.mark.asyncio
async def test_admin_always_has_permission():
    db = FakeDb(scalars=[_planning(), _machine()])
    result = await create_intervention_from_planning(
        planning_id=1, machine_id=1, problem_description="noisy",
        current_user=_user(UserRole.ADMIN), db=db,
    )
    assert result.id == 100


@pytest.mark.asyncio
async def test_technician_assigned_to_planning_has_permission():
    assignment = SimpleNamespace(id=1)
    db = FakeDb(scalars=[_planning(), _machine(), assignment])
    result = await create_intervention_from_planning(
        planning_id=1, machine_id=1, problem_description="noisy",
        current_user=_user(UserRole.TECHNICIEN, id=5), db=db,
    )
    assert result.id == 100


@pytest.mark.asyncio
async def test_technician_not_assigned_rejected():
    db = FakeDb(scalars=[_planning(), _machine(), None])
    with pytest.raises(HTTPException) as exc_info:
        await create_intervention_from_planning(
            planning_id=1, machine_id=1, problem_description="noisy",
            current_user=_user(UserRole.TECHNICIEN, id=5), db=db,
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_audit_failure_is_swallowed(monkeypatch):
    monkeypatch.setattr(
        iw_mod, "AuditService",
        lambda db: SimpleNamespace(log_create=AsyncMock(side_effect=RuntimeError("boom"))),
    )
    db = FakeDb(scalars=[_planning(), _machine()])
    result = await create_intervention_from_planning(
        planning_id=1, machine_id=1, problem_description="noisy",
        current_user=_user(UserRole.ADMIN), db=db,
    )
    assert result.id == 100  # non-fatal
