"""Unit tests for app/backend/modules/shared/routes/ordres_intervention/validation.py."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from models.alertes import Alert  # noqa: F401
import modules.shared.routes.ordres_intervention.validation as validation_mod
from modules.shared.routes.ordres_intervention.validation import (
    complete_validation_ordres_intervention,
    validate_OrdresIntervention,
)
from modules.shared.routes.ordres_intervention.schemas import (
    OrdresInterventionValidationData,
)


def _user(uid=1, nom="Chef"):
    return SimpleNamespace(id=uid, nom=nom)


def _intervention(**overrides):
    base = dict(
        id=1, machine_id=1, technician_id=2, statut="EN_ATTENTE",
        problem_description="desc", priority="MOYENNE", actual_failure_type=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture(autouse=True)
def _stub_audit(monkeypatch):
    monkeypatch.setattr(
        validation_mod, "AuditService", lambda db: SimpleNamespace(log_update=AsyncMock())
    )


# ── validate_OrdresIntervention: APPROVE ─────────────────────────────────────

@pytest.mark.asyncio
async def test_validate_approve_creates_linked_work_order(monkeypatch):
    intervention = _intervention()
    updated = SimpleNamespace(id=1, statut="APPROVED", ordre_travail_id=None)
    fake_service = SimpleNamespace(
        get_by_id=AsyncMock(return_value=intervention),
        update=AsyncMock(return_value=updated),
    )
    monkeypatch.setattr(validation_mod, "OrdresInterventionService", lambda db: fake_service)

    new_wo = SimpleNamespace(id=99)
    fake_wo_service = SimpleNamespace(create=AsyncMock(return_value=new_wo))
    monkeypatch.setattr("services.ordres_travail.OrdresTravailService", lambda db: fake_wo_service)

    data = OrdresInterventionValidationData(action="APPROVE")
    result = await validate_OrdresIntervention(1, data, db=object(), current_user=_user())

    assert result is updated
    fake_wo_service.create.assert_awaited_once()
    update_call = fake_service.update.call_args.args[1]
    assert update_call["statut"] == "APPROVED"
    assert update_call["ordre_travail_id"] == 99


@pytest.mark.asyncio
async def test_validate_approve_no_machine_id_raises_400(monkeypatch):
    """Regression: the 400 must reach the caller, not get swallowed into a 500
    by the generic `except Exception` (missing `except HTTPException: raise` guard —
    the same recurring bug pattern found in several other route files this session)."""
    intervention = _intervention(machine_id=None)
    fake_service = SimpleNamespace(
        get_by_id=AsyncMock(return_value=intervention), update=AsyncMock()
    )
    monkeypatch.setattr(validation_mod, "OrdresInterventionService", lambda db: fake_service)

    data = OrdresInterventionValidationData(action="APPROVE")
    with pytest.raises(HTTPException) as exc_info:
        await validate_OrdresIntervention(1, data, db=object(), current_user=_user())
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_validate_approve_wo_creation_failure_raises_500(monkeypatch):
    intervention = _intervention()
    fake_service = SimpleNamespace(
        get_by_id=AsyncMock(return_value=intervention), update=AsyncMock()
    )
    monkeypatch.setattr(validation_mod, "OrdresInterventionService", lambda db: fake_service)
    fake_wo_service = SimpleNamespace(create=AsyncMock(side_effect=RuntimeError("db down")))
    monkeypatch.setattr("services.ordres_travail.OrdresTravailService", lambda db: fake_wo_service)

    data = OrdresInterventionValidationData(action="APPROVE")
    with pytest.raises(HTTPException) as exc_info:
        await validate_OrdresIntervention(1, data, db=object(), current_user=_user())
    assert exc_info.value.status_code == 500


# ── validate_OrdresIntervention: REJECT ──────────────────────────────────────

@pytest.mark.asyncio
async def test_validate_reject_releases_reservations(monkeypatch):
    intervention = _intervention()
    updated = SimpleNamespace(id=1, statut="DECLINED")
    fake_service = SimpleNamespace(
        get_by_id=AsyncMock(return_value=intervention), update=AsyncMock(return_value=updated)
    )
    monkeypatch.setattr(validation_mod, "OrdresInterventionService", lambda db: fake_service)
    release_mock = AsyncMock()
    monkeypatch.setattr(
        validation_mod, "InventoryReservationService", lambda db: SimpleNamespace(release_all=release_mock)
    )

    data = OrdresInterventionValidationData(action="REJECT", rejection_reason="not needed")
    result = await validate_OrdresIntervention(1, data, db=object(), current_user=_user())

    assert result is updated
    release_mock.assert_awaited_once_with(intervention_id=1, reason="rejected", auto_commit=True)
    update_call = fake_service.update.call_args.args[1]
    assert update_call["statut"] == "DECLINED"
    assert update_call["rejection_reason"] == "not needed"


@pytest.mark.asyncio
async def test_validate_reject_swallows_release_failure(monkeypatch):
    intervention = _intervention()
    fake_service = SimpleNamespace(
        get_by_id=AsyncMock(return_value=intervention), update=AsyncMock(return_value=SimpleNamespace())
    )
    monkeypatch.setattr(validation_mod, "OrdresInterventionService", lambda db: fake_service)
    monkeypatch.setattr(
        validation_mod, "InventoryReservationService",
        lambda db: SimpleNamespace(release_all=AsyncMock(side_effect=RuntimeError("boom"))),
    )

    data = OrdresInterventionValidationData(action="REJECT")
    result = await validate_OrdresIntervention(1, data, db=object(), current_user=_user())
    assert result is not None  # did not raise


# ── validate_OrdresIntervention: shared paths ────────────────────────────────

@pytest.mark.asyncio
async def test_validate_not_found_raises_404(monkeypatch):
    fake_service = SimpleNamespace(get_by_id=AsyncMock(return_value=None))
    monkeypatch.setattr(validation_mod, "OrdresInterventionService", lambda db: fake_service)

    data = OrdresInterventionValidationData(action="APPROVE")
    with pytest.raises(HTTPException) as exc_info:
        await validate_OrdresIntervention(1, data, db=object(), current_user=_user())
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_validate_invalid_action_raises_400(monkeypatch):
    intervention = _intervention()
    fake_service = SimpleNamespace(get_by_id=AsyncMock(return_value=intervention))
    monkeypatch.setattr(validation_mod, "OrdresInterventionService", lambda db: fake_service)

    data = OrdresInterventionValidationData(action="MAYBE")
    with pytest.raises(HTTPException) as exc_info:
        await validate_OrdresIntervention(1, data, db=object(), current_user=_user())
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_validate_swallows_audit_log_failure(monkeypatch):
    intervention = _intervention()
    fake_service = SimpleNamespace(
        get_by_id=AsyncMock(return_value=intervention), update=AsyncMock(return_value=SimpleNamespace())
    )
    monkeypatch.setattr(validation_mod, "OrdresInterventionService", lambda db: fake_service)
    monkeypatch.setattr(
        validation_mod, "AuditService",
        lambda db: SimpleNamespace(log_update=AsyncMock(side_effect=RuntimeError("audit down"))),
    )

    data = OrdresInterventionValidationData(action="REJECT")
    result = await validate_OrdresIntervention(1, data, db=object(), current_user=_user())
    assert result is not None


# ── complete_validation_ordres_intervention ──────────────────────────────────

@pytest.mark.asyncio
async def test_complete_validation_success(monkeypatch):
    intervention = _intervention(statut="TERMINÉ", actual_failure_type="WEAR")
    updated = SimpleNamespace(id=1, statut="VALIDATED")
    fake_service = SimpleNamespace(
        get_by_id=AsyncMock(return_value=intervention), update=AsyncMock(return_value=updated)
    )
    monkeypatch.setattr(validation_mod, "OrdresInterventionService", lambda db: fake_service)

    result = await complete_validation_ordres_intervention(1, db=object(), current_user=_user())

    assert result is updated
    update_call = fake_service.update.call_args.args[1]
    assert update_call["statut"] == "VALIDATED"


@pytest.mark.asyncio
async def test_complete_validation_not_found_raises_404(monkeypatch):
    fake_service = SimpleNamespace(get_by_id=AsyncMock(return_value=None))
    monkeypatch.setattr(validation_mod, "OrdresInterventionService", lambda db: fake_service)

    with pytest.raises(HTTPException) as exc_info:
        await complete_validation_ordres_intervention(1, db=object(), current_user=_user())
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_complete_validation_wrong_status_raises_400(monkeypatch):
    intervention = _intervention(statut="EN_COURS", actual_failure_type="WEAR")
    fake_service = SimpleNamespace(get_by_id=AsyncMock(return_value=intervention))
    monkeypatch.setattr(validation_mod, "OrdresInterventionService", lambda db: fake_service)

    with pytest.raises(HTTPException) as exc_info:
        await complete_validation_ordres_intervention(1, db=object(), current_user=_user())
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_complete_validation_no_diagnosis_raises_400(monkeypatch):
    intervention = _intervention(statut="TERMINÉ", actual_failure_type=None)
    fake_service = SimpleNamespace(get_by_id=AsyncMock(return_value=intervention))
    monkeypatch.setattr(validation_mod, "OrdresInterventionService", lambda db: fake_service)

    with pytest.raises(HTTPException) as exc_info:
        await complete_validation_ordres_intervention(1, db=object(), current_user=_user())
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_complete_validation_swallows_audit_log_failure(monkeypatch):
    intervention = _intervention(statut="TERMINÉ", actual_failure_type="WEAR")
    fake_service = SimpleNamespace(
        get_by_id=AsyncMock(return_value=intervention),
        update=AsyncMock(return_value=SimpleNamespace()),
    )
    monkeypatch.setattr(validation_mod, "OrdresInterventionService", lambda db: fake_service)
    monkeypatch.setattr(
        validation_mod, "AuditService",
        lambda db: SimpleNamespace(log_update=AsyncMock(side_effect=RuntimeError("audit down"))),
    )

    result = await complete_validation_ordres_intervention(1, db=object(), current_user=_user())
    assert result is not None
