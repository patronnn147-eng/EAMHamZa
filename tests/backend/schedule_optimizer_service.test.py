"""Unit tests for app/backend/modules/ml/services/schedule_optimizer.py."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from models.alertes import Alert  # noqa: F401
from models.ordres_travail import OrdreStatut
import modules.ml.services.schedule_optimizer as sched_mod
from modules.ml.services.schedule_optimizer import (
    _wo_to_dict,
    compute_schedule,
    invalidate_schedule_cache,
)


@pytest.fixture(autouse=True)
def _reset_cache():
    invalidate_schedule_cache()
    yield
    invalidate_schedule_cache()


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class FakeDb:
    def __init__(self, execute_results):
        self._results = list(execute_results)

    async def execute(self, *_a, **_k):
        return self._results.pop(0)


def _wo(id=1, statut=OrdreStatut.ASSIGNED, date_debut=None, date_fin=None, priority=None, titre=None):
    return SimpleNamespace(id=id, statut=statut, date_debut=date_debut, date_fin=date_fin, priority=priority, titre=titre)


# ── _wo_to_dict ────────────────────────────────────────────────────────────────

def test_wo_to_dict_defaults_when_no_dates_or_priority():
    result = _wo_to_dict(_wo(id=5))
    assert result == {
        "id": 5, "priority": 3, "estimated_hours": 4.0, "parts_ready": True, "titre": "WO #5",
    }


def test_wo_to_dict_computes_estimated_hours_from_dates():
    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=10)
    result = _wo_to_dict(_wo(date_debut=start, date_fin=end))
    assert result["estimated_hours"] == 10.0


def test_wo_to_dict_ignores_out_of_range_duration():
    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=200)  # > 168h cap
    result = _wo_to_dict(_wo(date_debut=start, date_fin=end))
    assert result["estimated_hours"] == 4.0


def test_wo_to_dict_uses_numeric_priority():
    result = _wo_to_dict(_wo(priority="5"))
    assert result["priority"] == 5


def test_wo_to_dict_falls_back_to_default_priority_on_bad_value():
    result = _wo_to_dict(_wo(priority="not-a-number"))
    assert result["priority"] == 3


def test_wo_to_dict_uses_provided_title():
    result = _wo_to_dict(_wo(titre="Custom title"))
    assert result["titre"] == "Custom title"


# ── compute_schedule ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_compute_schedule_queries_active_statuses_only(monkeypatch):
    """Regression: OrdreStatut.PLANIFIE/EN_COURS don't exist on this enum —
    the real members are ASSIGNED/IN_PROGRESS. This used to raise
    AttributeError on every call, silently masked because forecast route
    tests always mock compute_schedule instead of calling the real thing."""
    captured_stmts = []

    class _CapturingDb(FakeDb):
        async def execute(self, stmt, *a, **k):
            captured_stmts.append(stmt)
            return self._results.pop(0)

    db = _CapturingDb([FakeResult([]), FakeResult([])])
    monkeypatch.setattr(sched_mod, "optimize_schedule", lambda *a, **k: {"assignments": []})

    await compute_schedule(db, horizon_days=7)
    compiled = str(captured_stmts[0].compile(compile_kwargs={"literal_binds": True}))
    assert "IN_PROGRESS" in compiled
    assert "ASSIGNED" in compiled


@pytest.mark.asyncio
async def test_compute_schedule_empty_returns_empty_assignments(monkeypatch):
    db = FakeDb([FakeResult([]), FakeResult([])])
    monkeypatch.setattr(
        sched_mod, "optimize_schedule",
        lambda work_orders, tech_ids, horizon_days: {"assignments": [], "makespan_days": 0, "solved": True},
    )
    result = await compute_schedule(db, horizon_days=7)
    assert result["assignments"] == []


@pytest.mark.asyncio
async def test_compute_schedule_backfills_titles(monkeypatch):
    wo = _wo(id=42, titre="Fix pump")
    tech = SimpleNamespace(id=9)
    db = FakeDb([FakeResult([wo]), FakeResult([tech])])
    monkeypatch.setattr(
        sched_mod, "optimize_schedule",
        lambda work_orders, tech_ids, horizon_days: {
            "assignments": [{"wo_id": 42, "tech_id": 9}], "makespan_days": 1, "solved": True,
        },
    )
    result = await compute_schedule(db, horizon_days=7)
    assert result["assignments"][0]["titre"] == "Fix pump"


@pytest.mark.asyncio
async def test_compute_schedule_defaults_tech_ids_when_none_found(monkeypatch):
    captured = {}
    db = FakeDb([FakeResult([]), FakeResult([])])

    def fake_optimize(work_orders, tech_ids, horizon_days):
        captured["tech_ids"] = tech_ids
        return {"assignments": []}

    monkeypatch.setattr(sched_mod, "optimize_schedule", fake_optimize)
    await compute_schedule(db, horizon_days=7)
    assert captured["tech_ids"] == [0]


@pytest.mark.asyncio
async def test_compute_schedule_returns_cached_result_within_ttl(monkeypatch):
    call_count = {"n": 0}

    def fake_optimize(*a, **k):
        call_count["n"] += 1
        return {"assignments": [], "run": call_count["n"]}

    monkeypatch.setattr(sched_mod, "optimize_schedule", fake_optimize)
    db = FakeDb([FakeResult([]), FakeResult([])])
    first = await compute_schedule(db, horizon_days=7)

    # Second call: no new execute() results queued — a cache miss would raise
    # IndexError from popping an empty list, proving the cache was used.
    second = await compute_schedule(db, horizon_days=7)
    assert second is first
    assert call_count["n"] == 1


@pytest.mark.asyncio
async def test_compute_schedule_recomputes_after_cache_expiry(monkeypatch):
    monkeypatch.setattr(sched_mod, "optimize_schedule", lambda *a, **k: {"assignments": []})
    db = FakeDb([FakeResult([]), FakeResult([]), FakeResult([]), FakeResult([])])
    await compute_schedule(db, horizon_days=7)

    sched_mod._SCHEDULE_CACHE["timestamp"] = datetime.now(timezone.utc) - timedelta(seconds=9999)
    result = await compute_schedule(db, horizon_days=7)
    assert result is not None
