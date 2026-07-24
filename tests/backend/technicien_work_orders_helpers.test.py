"""Unit tests for app/backend/modules/technicien/technicien_work_orders.py helpers."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from models.alertes import Alert  # noqa: F401 — registers Alert mapper (needed by Utilisateurs relationship)
from modules.technicien.technicien_work_orders import (
    _add_telemetry_if_present,
    _check_wo_access,
    _fulfill_reserved_parts,
    _snapshot_pre_completion,
    _submit_pending_pieces,
    _try_audit_complete,
    _try_audit_start,
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


# ── _try_audit_start / _try_audit_complete ─────────────────────────────────────

@pytest.mark.asyncio
async def test_try_audit_start_logs_success(monkeypatch):
    log_mock = AsyncMock()
    monkeypatch.setattr(
        "modules.technicien.technicien_work_orders.AuditService",
        lambda db: SimpleNamespace(log_update=log_mock),
    )
    wo = SimpleNamespace(titre="WO1")
    await _try_audit_start(FakeDb([]), order_id=1, previous_statut="ASSIGNED", wo=wo, user_id=2, nom="Bob")
    log_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_try_audit_start_swallows_failure(monkeypatch):
    monkeypatch.setattr(
        "modules.technicien.technicien_work_orders.AuditService",
        lambda db: SimpleNamespace(log_update=AsyncMock(side_effect=RuntimeError("boom"))),
    )
    wo = SimpleNamespace(titre="WO1")
    await _try_audit_start(FakeDb([]), order_id=1, previous_statut="ASSIGNED", wo=wo, user_id=2, nom="Bob")  # no raise


@pytest.mark.asyncio
async def test_try_audit_complete_logs_success(monkeypatch):
    log_mock = AsyncMock()
    monkeypatch.setattr(
        "modules.technicien.technicien_work_orders.AuditService",
        lambda db: SimpleNamespace(log_update=log_mock),
    )
    wo = SimpleNamespace(titre="WO1")
    payload = SimpleNamespace(rapport="All fixed")
    await _try_audit_complete(FakeDb([]), order_id=1, payload=payload, wo=wo, user_id=2, nom="Bob")
    log_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_try_audit_complete_swallows_failure(monkeypatch):
    monkeypatch.setattr(
        "modules.technicien.technicien_work_orders.AuditService",
        lambda db: SimpleNamespace(log_update=AsyncMock(side_effect=RuntimeError("boom"))),
    )
    wo = SimpleNamespace(titre="WO1")
    payload = SimpleNamespace(rapport="All fixed")
    await _try_audit_complete(FakeDb([]), order_id=1, payload=payload, wo=wo, user_id=2, nom="Bob")  # no raise


# ── _snapshot_pre_completion ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_snapshot_pre_completion_sets_health_score(monkeypatch):
    monkeypatch.setattr(
        "modules.technicien.technicien_work_orders.PostMaintenanceRecoveryService",
        lambda db: SimpleNamespace(snapshot_health=AsyncMock(return_value=87.5)),
    )
    wo = SimpleNamespace(machine_id=1, health_score_at_completion=None)
    await _snapshot_pre_completion(FakeDb([]), wo, order_id=1)
    assert wo.health_score_at_completion == 87.5


@pytest.mark.asyncio
async def test_snapshot_pre_completion_none_score_leaves_untouched(monkeypatch):
    monkeypatch.setattr(
        "modules.technicien.technicien_work_orders.PostMaintenanceRecoveryService",
        lambda db: SimpleNamespace(snapshot_health=AsyncMock(return_value=None)),
    )
    wo = SimpleNamespace(machine_id=1, health_score_at_completion="unchanged")
    await _snapshot_pre_completion(FakeDb([]), wo, order_id=1)
    assert wo.health_score_at_completion == "unchanged"


@pytest.mark.asyncio
async def test_snapshot_pre_completion_swallows_failure(monkeypatch):
    monkeypatch.setattr(
        "modules.technicien.technicien_work_orders.PostMaintenanceRecoveryService",
        lambda db: SimpleNamespace(snapshot_health=AsyncMock(side_effect=RuntimeError("x"))),
    )
    wo = SimpleNamespace(machine_id=1, health_score_at_completion=None)
    await _snapshot_pre_completion(FakeDb([]), wo, order_id=1)  # no raise


# ── _submit_pending_pieces ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_pending_pieces_noop_without_intervention():
    payload = SimpleNamespace(pending_pieces_direct=[SimpleNamespace(name="Bolt")])
    await _submit_pending_pieces(FakeDb([]), None, payload, user_id=1, order_id=1)  # no-op, no raise


@pytest.mark.asyncio
async def test_submit_pending_pieces_noop_without_items():
    intervention = SimpleNamespace(id=1)
    payload = SimpleNamespace(pending_pieces_direct=None)
    await _submit_pending_pieces(FakeDb([]), intervention, payload, user_id=1, order_id=1)


@pytest.mark.asyncio
async def test_submit_pending_pieces_skips_blank_names_and_submits_valid(monkeypatch):
    create_mock = AsyncMock()
    monkeypatch.setattr(
        "services.inventory.PendingPieceService",
        lambda db: SimpleNamespace(create_with_placeholder=create_mock),
    )
    intervention = SimpleNamespace(id=5)
    payload = SimpleNamespace(pending_pieces_direct=[
        SimpleNamespace(name="   ", quantity=1, unit="pcs", category="misc", notes=None),
        SimpleNamespace(name="Bolt M6", quantity=2, unit="pcs", category="misc", notes="extra"),
    ])
    await _submit_pending_pieces(FakeDb([]), intervention, payload, user_id=9, order_id=1)
    create_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_submit_pending_pieces_swallows_failure(monkeypatch):
    monkeypatch.setattr(
        "services.inventory.PendingPieceService",
        lambda db: SimpleNamespace(create_with_placeholder=AsyncMock(side_effect=RuntimeError("x"))),
    )
    intervention = SimpleNamespace(id=5)
    payload = SimpleNamespace(pending_pieces_direct=[
        SimpleNamespace(name="Bolt", quantity=1, unit="pcs", category=None, notes=None),
    ])
    await _submit_pending_pieces(FakeDb([]), intervention, payload, user_id=9, order_id=1)  # no raise


# ── _fulfill_reserved_parts ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fulfill_reserved_parts_noop_without_intervention():
    payload = SimpleNamespace(parts_consumed=[SimpleNamespace()])
    await _fulfill_reserved_parts(FakeDb([]), None, payload, order_id=1)  # no-op


@pytest.mark.asyncio
async def test_fulfill_reserved_parts_noop_without_items():
    intervention = SimpleNamespace(id=1)
    payload = SimpleNamespace(parts_consumed=None)
    await _fulfill_reserved_parts(FakeDb([]), intervention, payload, order_id=1)


@pytest.mark.asyncio
async def test_fulfill_reserved_parts_success_fulfills_each_item(monkeypatch):
    fulfill_mock = AsyncMock()
    monkeypatch.setattr(
        "modules.technicien.technicien_work_orders.InventoryReservationService",
        lambda db: SimpleNamespace(fulfill_reservation=fulfill_mock),
    )
    monkeypatch.setattr("modules.ml.services.demand_forecast.invalidate_forecast_cache", lambda: None)
    intervention = SimpleNamespace(id=1)
    item = SimpleNamespace(
        required_piece_id=1, quantity_used=2, quantity_returned=0,
        quantity_wasted=0, disposition="used", notes=None,
    )
    payload = SimpleNamespace(parts_consumed=[item])
    await _fulfill_reserved_parts(FakeDb([]), intervention, payload, order_id=1)
    fulfill_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_fulfill_reserved_parts_value_error_rolls_back_and_raises_400(monkeypatch):
    monkeypatch.setattr(
        "modules.technicien.technicien_work_orders.InventoryReservationService",
        lambda db: SimpleNamespace(fulfill_reservation=AsyncMock(side_effect=ValueError("insufficient stock"))),
    )
    db = FakeDb([])
    db.rollback = AsyncMock()
    intervention = SimpleNamespace(id=1)
    item = SimpleNamespace(
        required_piece_id=1, quantity_used=2, quantity_returned=0,
        quantity_wasted=0, disposition="used", notes=None,
    )
    payload = SimpleNamespace(parts_consumed=[item])
    with pytest.raises(HTTPException) as exc_info:
        await _fulfill_reserved_parts(db, intervention, payload, order_id=1)
    assert exc_info.value.status_code == 400
    db.rollback.assert_awaited_once()
