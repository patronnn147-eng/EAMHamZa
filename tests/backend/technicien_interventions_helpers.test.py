"""Unit tests for app/backend/modules/technicien/routes/interventions.py helpers."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from models.alertes import Alert  # noqa: F401
from models.ordres_intervention import OrdresIntervention
from models.ordres_travail import OrdreStatut
from modules.technicien.routes.interventions import (
    InterventionRequestPayload,
    InterventionStatusUpdate,
    _apply_intervention_dates,
    _notify_status_change,
    _propagate_wo_status,
    _validate_status_transition,
    list_my_interventions,
    request_intervention,
    update_intervention_status,
)


def _intervention(statut="APPROVED", date_debut=None, date_fin=None):
    return SimpleNamespace(statut=statut, date_debut=date_debut, date_fin=date_fin)


def _update(statut, date_debut=None, date_fin=None):
    return SimpleNamespace(statut=statut, date_debut=date_debut, date_fin=date_fin)


# ── _validate_status_transition ───────────────────────────────────────────────

def test_validate_status_transition_rejects_unknown_status():
    with pytest.raises(HTTPException) as exc_info:
        _validate_status_transition(_intervention(), _update("NOT_A_STATUS"))
    assert exc_info.value.status_code == 400


def test_validate_status_transition_rejects_start_without_approval():
    with pytest.raises(HTTPException) as exc_info:
        _validate_status_transition(_intervention(statut="EN_ATTENTE"), _update("EN_COURS"))
    assert "approved by ChefTech" in exc_info.value.detail


def test_validate_status_transition_allows_start_when_approved():
    _validate_status_transition(_intervention(statut="APPROVED"), _update("EN_COURS"))  # no raise


def test_validate_status_transition_allows_already_in_progress_to_stay():
    _validate_status_transition(_intervention(statut="EN_COURS"), _update("EN_COURS"))  # no raise


def test_validate_status_transition_rejects_starting_declined_intervention():
    # The "must be approved first" guard fires before the declined-specific
    # check, since DECLINED isn't in the allowed-to-start set either - still
    # a 400, just via the first matching guard clause.
    with pytest.raises(HTTPException) as exc_info:
        _validate_status_transition(_intervention(statut="DECLINED"), _update("EN_COURS"))
    assert exc_info.value.status_code == 400


def test_validate_status_transition_rejects_completing_declined_intervention():
    with pytest.raises(HTTPException):
        _validate_status_transition(_intervention(statut="DECLINED"), _update("TERMINÉ"))


def test_validate_status_transition_allows_blocking_declined_intervention():
    _validate_status_transition(_intervention(statut="DECLINED"), _update("BLOQUÉ"))  # no raise


# ── _apply_intervention_dates ─────────────────────────────────────────────────

def test_apply_intervention_dates_sets_date_debut_on_start():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    intervention = _intervention(date_debut=None)
    _apply_intervention_dates(intervention, _update("EN_COURS"), now)
    assert intervention.date_debut == now


def test_apply_intervention_dates_does_not_overwrite_existing_date_debut_on_start():
    existing = datetime(2025, 1, 1, tzinfo=timezone.utc)
    intervention = _intervention(date_debut=existing)
    _apply_intervention_dates(intervention, _update("EN_COURS"), datetime.now(timezone.utc))
    assert intervention.date_debut == existing


def test_apply_intervention_dates_sets_both_dates_on_completion():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    intervention = _intervention(date_debut=None, date_fin=None)
    _apply_intervention_dates(intervention, _update("TERMINÉ"), now)
    assert intervention.date_debut == now
    assert intervention.date_fin == now


def test_apply_intervention_dates_uses_provided_dates_when_given():
    provided_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    provided_end = datetime(2026, 1, 2, tzinfo=timezone.utc)
    intervention = _intervention(date_debut=None, date_fin=None)
    _apply_intervention_dates(intervention, _update("TERMINÉ", date_debut=provided_start, date_fin=provided_end), datetime.now(timezone.utc))
    assert intervention.date_debut == provided_start
    assert intervention.date_fin == provided_end


def test_apply_intervention_dates_blocked_sets_date_debut_if_missing():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    intervention = _intervention(date_debut=None)
    _apply_intervention_dates(intervention, _update("BLOQUÉ"), now)
    assert intervention.date_debut == now


def test_apply_intervention_dates_unrelated_status_is_noop():
    intervention = _intervention(date_debut=None, date_fin=None)
    _apply_intervention_dates(intervention, _update("EN_ATTENTE"), datetime.now(timezone.utc))
    assert intervention.date_debut is None
    assert intervention.date_fin is None


# ── _notify_status_change ─────────────────────────────────────────────────────

class FakeScalarsResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class FakeDb:
    def __init__(self, execute_results=None, scalars=None):
        self._results = list(execute_results or [])
        self._scalars = list(scalars or [])
        self.committed = 0

    async def execute(self, *_a, **_k):
        return self._results.pop(0)

    async def scalar(self, *_a, **_k):
        return self._scalars.pop(0)

    async def commit(self):
        self.committed += 1


@pytest.mark.asyncio
async def test_notify_status_change_publishes_and_dispatches(monkeypatch):
    fake_rmq = SimpleNamespace(publish_intervention_event=AsyncMock())
    monkeypatch.setattr(
        "modules.technicien.routes.interventions.get_rabbitmq", AsyncMock(return_value=fake_rmq)
    )
    fake_notify = SimpleNamespace(delay=lambda *a, **k: None)
    monkeypatch.setattr("modules.technicien.routes.interventions.notify_intervention_status_changed", fake_notify)

    cheftech = SimpleNamespace(email="ct@x.com", nom="CT")
    db = FakeDb(execute_results=[FakeScalarsResult([cheftech])])
    intervention = SimpleNamespace(id=1, ordre_travail_id=2)
    current_user = SimpleNamespace(id=1, nom="Bob", email="bob@x.com")

    await _notify_status_change(db, current_user, intervention, "EN_ATTENTE", "EN_COURS")
    fake_rmq.publish_intervention_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_notify_status_change_swallows_rabbitmq_failure(monkeypatch):
    monkeypatch.setattr(
        "modules.technicien.routes.interventions.get_rabbitmq",
        AsyncMock(side_effect=RuntimeError("rmq down")),
    )
    db = FakeDb(execute_results=[FakeScalarsResult([])])
    intervention = SimpleNamespace(id=1, ordre_travail_id=2)
    current_user = SimpleNamespace(id=1, nom="Bob", email="bob@x.com")
    # must not raise
    await _notify_status_change(db, current_user, intervention, "EN_ATTENTE", "EN_COURS")


@pytest.mark.asyncio
async def test_notify_status_change_swallows_celery_dispatch_failure(monkeypatch):
    fake_rmq = SimpleNamespace(publish_intervention_event=AsyncMock())
    monkeypatch.setattr(
        "modules.technicien.routes.interventions.get_rabbitmq", AsyncMock(return_value=fake_rmq)
    )

    class FakeDbRaising(FakeDb):
        async def execute(self, *_a, **_k):
            raise RuntimeError("db down")

    db = FakeDbRaising()
    intervention = SimpleNamespace(id=1, ordre_travail_id=2)
    current_user = SimpleNamespace(id=1, nom="Bob", email="bob@x.com")
    await _notify_status_change(db, current_user, intervention, "EN_ATTENTE", "EN_COURS")  # must not raise


# ── _propagate_wo_status ───────────────────────────────────────────────────────

def _stats_row(total=0, done=0, in_progress=0, blocked=0):
    return SimpleNamespace(total=total, done=done, in_progress=in_progress, blocked=blocked)


class FakeStatsResult:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


@pytest.mark.asyncio
async def test_propagate_wo_status_no_ordre_is_noop():
    db = FakeDb(scalars=[None])
    await _propagate_wo_status(db, ordre_id=1)
    assert db.committed == 0


@pytest.mark.asyncio
async def test_propagate_wo_status_blocked_leaves_wo_status_untouched():
    # No WO-level "blocked" status exists in OrdreStatut, so a blocked
    # intervention must not overwrite the parent work order's status.
    ordre = SimpleNamespace(statut=OrdreStatut.IN_PROGRESS)
    db = FakeDb(scalars=[ordre], execute_results=[FakeStatsResult(_stats_row(total=3, done=1, in_progress=1, blocked=1))])
    await _propagate_wo_status(db, ordre_id=1)
    assert ordre.statut == OrdreStatut.IN_PROGRESS
    assert db.committed == 1


@pytest.mark.asyncio
async def test_propagate_wo_status_all_done_marks_completed():
    ordre = SimpleNamespace(statut=OrdreStatut.IN_PROGRESS)
    db = FakeDb(scalars=[ordre], execute_results=[FakeStatsResult(_stats_row(total=2, done=2))])
    await _propagate_wo_status(db, ordre_id=1)
    assert ordre.statut == OrdreStatut.COMPLETED


@pytest.mark.asyncio
async def test_propagate_wo_status_some_in_progress():
    ordre = SimpleNamespace(statut=OrdreStatut.ASSIGNED)
    db = FakeDb(scalars=[ordre], execute_results=[FakeStatsResult(_stats_row(total=3, done=1, in_progress=1))])
    await _propagate_wo_status(db, ordre_id=1)
    assert ordre.statut == OrdreStatut.IN_PROGRESS


@pytest.mark.asyncio
async def test_propagate_wo_status_none_started_stays_assigned():
    ordre = SimpleNamespace(statut=OrdreStatut.ASSIGNED)
    db = FakeDb(scalars=[ordre], execute_results=[FakeStatsResult(_stats_row(total=2, done=0))])
    await _propagate_wo_status(db, ordre_id=1)
    assert ordre.statut == OrdreStatut.ASSIGNED


@pytest.mark.asyncio
async def test_propagate_wo_status_no_interventions_leaves_status_untouched():
    ordre = SimpleNamespace(statut=OrdreStatut.DRAFT)
    db = FakeDb(scalars=[ordre], execute_results=[FakeStatsResult(_stats_row(total=0, done=0))])
    await _propagate_wo_status(db, ordre_id=1)
    assert ordre.statut == OrdreStatut.DRAFT
    assert db.committed == 1


# ── route handlers ──────────────────────────────────────────────────────────

class FakeQueryResult:
    def __init__(self, scalar_value=None, scalars_list=None, rows_list=None):
        self._scalar_value = scalar_value
        self._scalars_list = scalars_list
        self._rows_list = rows_list

    def scalar(self):
        return self._scalar_value

    def scalars(self):
        return FakeScalarsResult(self._scalars_list or [])

    def all(self):
        return self._rows_list or []


class FakeSession(FakeDb):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.refreshed = 0
        self.flushed = 0
        self.added = []

    async def refresh(self, *_a, **_k):
        self.refreshed += 1

    async def flush(self):
        self.flushed += 1

    def add(self, obj):
        self.added.append(obj)


def _intervention_model(**overrides):
    defaults = dict(
        id=1, ordre_travail_id=None, statut="APPROVED",
        date_intervention=datetime(2026, 1, 1, tzinfo=timezone.utc),
        technician_id=1, legacy_parts_text=None,
    )
    defaults.update(overrides)
    return OrdresIntervention(**defaults)


# -- list_my_interventions --

@pytest.mark.asyncio
async def test_list_my_interventions_empty():
    user = SimpleNamespace(id=1)
    db = FakeDb(execute_results=[
        FakeQueryResult(scalar_value=0),
        FakeQueryResult(scalars_list=[]),
    ])
    resp = await list_my_interventions(page=1, size=10, statut=None, _current_user=user, db=db)
    assert resp.total == 0
    assert resp.items == []


@pytest.mark.asyncio
async def test_list_my_interventions_marks_overdue_item():
    user = SimpleNamespace(id=1)
    past_due = datetime(2020, 1, 1, tzinfo=timezone.utc)
    item = _intervention_model(id=7, ordre_travail_id=9, statut="EN_COURS")
    db = FakeDb(execute_results=[
        FakeQueryResult(scalar_value=1),
        FakeQueryResult(scalars_list=[item]),
        FakeQueryResult(rows_list=[SimpleNamespace(id=9, date_echeance=past_due)]),
    ])
    resp = await list_my_interventions(page=1, size=10, statut=None, _current_user=user, db=db)
    assert resp.total == 1
    assert resp.items[0]["is_overdue"] is True


@pytest.mark.asyncio
async def test_list_my_interventions_done_item_not_overdue():
    user = SimpleNamespace(id=1)
    past_due = datetime(2020, 1, 1, tzinfo=timezone.utc)
    item = _intervention_model(
        id=8, ordre_travail_id=9, statut="TERMINÉ",
        date_fin=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    db = FakeDb(execute_results=[
        FakeQueryResult(scalar_value=1),
        FakeQueryResult(scalars_list=[item]),
        FakeQueryResult(rows_list=[SimpleNamespace(id=9, date_echeance=past_due)]),
    ])
    resp = await list_my_interventions(page=1, size=10, statut="TERMINÉ", _current_user=user, db=db)
    assert resp.items[0]["is_overdue"] is False


# -- update_intervention_status --

@pytest.mark.asyncio
async def test_update_intervention_status_not_found_raises_404():
    db = FakeSession(scalars=[None])
    user = SimpleNamespace(id=1)
    data = InterventionStatusUpdate(statut="EN_COURS")
    with pytest.raises(HTTPException) as exc_info:
        await update_intervention_status(intervention_id=99, data=data, current_user=user, db=db)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_intervention_status_invalid_transition_raises_400():
    intervention = _intervention_model(statut="EN_ATTENTE")
    db = FakeSession(scalars=[intervention])
    user = SimpleNamespace(id=1)
    data = InterventionStatusUpdate(statut="EN_COURS")
    with pytest.raises(HTTPException) as exc_info:
        await update_intervention_status(intervention_id=1, data=data, current_user=user, db=db)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_update_intervention_status_same_status_skips_notify_and_propagates(monkeypatch):
    # statut unchanged (APPROVED -> APPROVED): no notify call needed, and no
    # feedback hooks fire since APPROVED isn't a terminal status.
    intervention = _intervention_model(statut="APPROVED", ordre_travail_id=5)
    db = FakeSession(scalars=[intervention, None], execute_results=[])
    user = SimpleNamespace(id=1)
    data = InterventionStatusUpdate(statut="APPROVED")

    result = await update_intervention_status(intervention_id=1, data=data, current_user=user, db=db)

    assert result.statut == "APPROVED"
    assert db.refreshed == 1
    assert db.committed == 1  # only the main commit; _propagate_wo_status found no ordre


@pytest.mark.asyncio
async def test_update_intervention_status_completion_triggers_feedback_and_notify(monkeypatch):
    fake_rmq = SimpleNamespace(publish_intervention_event=AsyncMock())
    monkeypatch.setattr("modules.technicien.routes.interventions.get_rabbitmq", AsyncMock(return_value=fake_rmq))
    monkeypatch.setattr(
        "modules.technicien.routes.interventions.notify_intervention_status_changed",
        SimpleNamespace(delay=lambda *a, **k: None),
    )
    monkeypatch.setattr("modules.ml.services.p7_feedback.record_p7_feedback", AsyncMock())
    monkeypatch.setattr("modules.ml.services.p4_feedback.record_p4_feedback", AsyncMock())

    intervention = _intervention_model(statut="EN_COURS", ordre_travail_id=None, legacy_parts_text="pump seal x1")
    cheftech = SimpleNamespace(email="ct@x.com", nom="CT")
    db = FakeSession(
        scalars=[intervention, None],
        execute_results=[FakeScalarsResult([cheftech])],
    )
    user = SimpleNamespace(id=1, nom="Bob", email="bob@x.com")
    data = InterventionStatusUpdate(statut="TERMINÉ")

    result = await update_intervention_status(intervention_id=1, data=data, current_user=user, db=db)

    assert result.statut == "TERMINÉ"
    assert result.date_fin is not None
    fake_rmq.publish_intervention_event.assert_awaited_once()


# -- request_intervention --

@pytest.mark.asyncio
async def test_request_intervention_creates_new_when_none_found(monkeypatch):
    monkeypatch.setattr(
        "modules.technicien.routes.interventions.get_rabbitmq",
        AsyncMock(side_effect=RuntimeError("rmq down")),
    )
    # payload.ordre_travail_id is unset, so the existing-intervention lookup
    # is never issued — the route goes straight to creating a new record.
    db = FakeSession(execute_results=[FakeScalarsResult([])])
    user = SimpleNamespace(id=1, nom="Bob", email="bob@x.com")
    payload = InterventionRequestPayload(
        machine_id=3, problem_description="noisy bearing", priority="ÉLEVÉE",
    )

    result = await request_intervention(payload=payload, current_user=user, db=db)

    assert result.statut == "PENDING_APPROVAL"
    assert result.technician_id == 1
    assert db.flushed == 1
    assert len(db.added) == 1


@pytest.mark.asyncio
async def test_request_intervention_re_requests_existing_declined(monkeypatch):
    monkeypatch.setattr(
        "modules.technicien.routes.interventions.get_rabbitmq",
        AsyncMock(side_effect=RuntimeError("rmq down")),
    )
    existing = _intervention_model(id=4, statut="DECLINED", ordre_travail_id=5)
    db = FakeSession(scalars=[existing], execute_results=[FakeScalarsResult([])])
    user = SimpleNamespace(id=1, nom="Bob", email="bob@x.com")
    payload = InterventionRequestPayload(
        ordre_travail_id=5, machine_id=3, problem_description="still noisy", priority="ÉLEVÉE",
    )

    result = await request_intervention(payload=payload, current_user=user, db=db)

    assert result.statut == "PENDING_APPROVAL"
    assert result.rejection_reason is None


@pytest.mark.asyncio
async def test_request_intervention_rejects_when_already_in_flight(monkeypatch):
    existing = _intervention_model(id=4, statut="EN_COURS", ordre_travail_id=5)
    db = FakeSession(scalars=[existing])
    user = SimpleNamespace(id=1, nom="Bob", email="bob@x.com")
    payload = InterventionRequestPayload(
        ordre_travail_id=5, machine_id=3, problem_description="still noisy", priority="ÉLEVÉE",
    )

    with pytest.raises(HTTPException) as exc_info:
        await request_intervention(payload=payload, current_user=user, db=db)
    assert exc_info.value.status_code == 400
