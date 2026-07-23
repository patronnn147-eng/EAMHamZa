"""Unit tests for app/backend/modules/technicien/routes/interventions.py helpers."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from modules.technicien.routes.interventions import (
    _apply_intervention_dates,
    _notify_status_change,
    _propagate_wo_status,
    _validate_status_transition,
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
async def test_propagate_wo_status_blocked_wins():
    ordre = SimpleNamespace(statut="EN_COURS")
    db = FakeDb(scalars=[ordre], execute_results=[FakeStatsResult(_stats_row(total=3, done=1, in_progress=1, blocked=1))])
    await _propagate_wo_status(db, ordre_id=1)
    assert ordre.statut == "BLOQUÉ"
    assert db.committed == 1


@pytest.mark.asyncio
async def test_propagate_wo_status_all_done_marks_terminated():
    ordre = SimpleNamespace(statut="EN_COURS")
    db = FakeDb(scalars=[ordre], execute_results=[FakeStatsResult(_stats_row(total=2, done=2))])
    await _propagate_wo_status(db, ordre_id=1)
    assert ordre.statut == "TERMINÉ"


@pytest.mark.asyncio
async def test_propagate_wo_status_some_in_progress():
    ordre = SimpleNamespace(statut="ASSIGNÉ")
    db = FakeDb(scalars=[ordre], execute_results=[FakeStatsResult(_stats_row(total=3, done=1, in_progress=1))])
    await _propagate_wo_status(db, ordre_id=1)
    assert ordre.statut == "EN_COURS"


@pytest.mark.asyncio
async def test_propagate_wo_status_none_started_stays_assigned():
    ordre = SimpleNamespace(statut="ASSIGNÉ")
    db = FakeDb(scalars=[ordre], execute_results=[FakeStatsResult(_stats_row(total=2, done=0))])
    await _propagate_wo_status(db, ordre_id=1)
    assert ordre.statut == "ASSIGNÉ"
