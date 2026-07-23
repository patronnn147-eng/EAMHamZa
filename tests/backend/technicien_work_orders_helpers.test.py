"""Unit tests for app/backend/modules/technicien/technicien_work_orders.py helpers."""
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from models.alertes import Alert  # noqa: F401 — registers Alert mapper (needed by Utilisateurs relationship)
from modules.technicien.technicien_work_orders import (
    _add_telemetry_if_present,
    _check_wo_access,
    _update_intervention_fields,
    _update_intervention_on_start,
)


class FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeDb:
    def __init__(self, execute_results=None, scalars=None):
        self._results = list(execute_results or [])
        self._scalars = list(scalars or [])
        self.added = []

    async def execute(self, *_a, **_k):
        return self._results.pop(0)

    async def scalar(self, *_a, **_k):
        return self._scalars.pop(0)

    def add(self, obj):
        self.added.append(obj)


# ── _update_intervention_on_start ─────────────────────────────────────────────

def test_update_intervention_on_start_sets_status_and_date():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    intervention = SimpleNamespace(statut="APPROVED", date_debut=None)
    _update_intervention_on_start(intervention, now)
    assert intervention.statut == "EN_COURS"
    assert intervention.date_debut == now


def test_update_intervention_on_start_preserves_existing_date():
    existing = datetime(2025, 1, 1, tzinfo=timezone.utc)
    intervention = SimpleNamespace(statut="APPROVED", date_debut=existing)
    _update_intervention_on_start(intervention, datetime.now(timezone.utc))
    assert intervention.date_debut == existing


# ── _check_wo_access ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_wo_access_owner_shortcuts_true():
    wo = SimpleNamespace(utilisateur_id=5)
    db = FakeDb([])  # no execute call needed
    assert await _check_wo_access(db, wo, user_id=5, order_id=1) is True


@pytest.mark.asyncio
async def test_check_wo_access_linked_via_intervention():
    wo = SimpleNamespace(utilisateur_id=999)
    db = FakeDb([FakeScalarResult(SimpleNamespace(id=1))])
    assert await _check_wo_access(db, wo, user_id=5, order_id=1) is True


@pytest.mark.asyncio
async def test_check_wo_access_denied():
    wo = SimpleNamespace(utilisateur_id=999)
    db = FakeDb([FakeScalarResult(None)])
    assert await _check_wo_access(db, wo, user_id=5, order_id=1) is False


# ── _update_intervention_fields ───────────────────────────────────────────────

def _payload(**overrides):
    base = dict(
        rapport="Fixed it", intervention_type="CORRECTIVE", root_cause_category="MECH",
        root_cause_description="Worn belt", actions_performed="Replaced belt",
        parts_replaced="belt x1", tools_used="wrench", machine_status_after="OPERATIONNELLE",
        plan_hypothesis="Belt wear", check_resolved=True, check_verification_method="Visual",
        act_preventive_actions="Schedule inspection", act_recommendations="Check monthly",
        ml_prediction_matched=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_update_intervention_fields_sets_completion_status():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    intervention = SimpleNamespace(statut="EN_COURS", date_debut=None, date_fin=None, planning_tache_id=None)
    db = FakeDb([])
    await _update_intervention_fields(db, intervention, _payload(), wo_date_debut=None, now=now)
    assert intervention.statut == "TERMINÉ"
    assert intervention.date_debut == now
    assert intervention.date_fin == now
    assert intervention.rapport == "Fixed it"


@pytest.mark.asyncio
async def test_update_intervention_fields_preserves_existing_date_debut():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    existing_start = datetime(2025, 12, 1, tzinfo=timezone.utc)
    intervention = SimpleNamespace(statut="EN_COURS", date_debut=existing_start, date_fin=None, planning_tache_id=None)
    db = FakeDb([])
    await _update_intervention_fields(db, intervention, _payload(), wo_date_debut=None, now=now)
    assert intervention.date_debut == existing_start


@pytest.mark.asyncio
async def test_update_intervention_fields_completes_linked_planning_tache():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    intervention = SimpleNamespace(statut="EN_COURS", date_debut=None, date_fin=None, planning_tache_id=7)
    tache = SimpleNamespace(id=7, statut="IN_PROGRESS")
    db = FakeDb(scalars=[tache])
    await _update_intervention_fields(db, intervention, _payload(), wo_date_debut=None, now=now)
    assert tache.statut == "COMPLETED"


@pytest.mark.asyncio
async def test_update_intervention_fields_ml_prediction_matched_only_set_when_given():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    intervention = SimpleNamespace(
        statut="EN_COURS", date_debut=None, date_fin=None, planning_tache_id=None,
        ml_prediction_matched="OLD_VALUE",
    )
    db = FakeDb([])
    await _update_intervention_fields(db, intervention, _payload(ml_prediction_matched=None), wo_date_debut=None, now=now)
    assert intervention.ml_prediction_matched == "OLD_VALUE"  # untouched


@pytest.mark.asyncio
async def test_update_intervention_fields_ml_prediction_matched_updates_when_given():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    intervention = SimpleNamespace(
        statut="EN_COURS", date_debut=None, date_fin=None, planning_tache_id=None,
        ml_prediction_matched=None,
    )
    db = FakeDb([])
    await _update_intervention_fields(db, intervention, _payload(ml_prediction_matched=True), wo_date_debut=None, now=now)
    assert intervention.ml_prediction_matched is True


# ── _add_telemetry_if_present ──────────────────────────────────────────────────

def test_add_telemetry_if_present_noop_when_all_fields_absent():
    db = FakeDb([])
    payload = SimpleNamespace(
        air_temperature=None, process_temperature=None, rotational_speed=None,
        torque=None, tool_wear=None, telemetry_notes=None,
    )
    wo = SimpleNamespace(machine_id=1, id=2)
    _add_telemetry_if_present(db, wo, technician_id=3, payload=payload, now=datetime.now(timezone.utc))
    assert db.added == []


def test_add_telemetry_if_present_adds_row_when_any_field_present():
    db = FakeDb([])
    payload = SimpleNamespace(
        air_temperature=300.0, process_temperature=None, rotational_speed=None,
        torque=None, tool_wear=None, telemetry_notes="manual entry",
    )
    wo = SimpleNamespace(machine_id=1, id=2)
    _add_telemetry_if_present(db, wo, technician_id=3, payload=payload, now=datetime.now(timezone.utc))
    assert len(db.added) == 1
    assert db.added[0].air_temperature == 300.0
    assert db.added[0].torque == 0  # defaulted since not provided
