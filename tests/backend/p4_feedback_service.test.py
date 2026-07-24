"""Unit tests for app/backend/modules/ml/services/p4_feedback.py."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from models.alertes import Alert  # noqa: F401 — registers Alert mapper (needed by Utilisateurs relationship)
from modules.ml.services.p4_feedback import record_p4_feedback


class FakeResult:
    def __init__(self, scalar_one_or_none=None):
        self._soo = scalar_one_or_none

    def scalar_one_or_none(self):
        return self._soo


class FakeDb:
    def __init__(self, execute_results=None):
        self._results = list(execute_results or [])
        self.committed = 0
        self.rolled_back = 0

    async def execute(self, *_a, **_k):
        return self._results.pop(0)

    async def commit(self):
        self.committed += 1

    async def rollback(self):
        self.rolled_back += 1


@pytest.mark.asyncio
async def test_intervention_not_found_returns_none():
    db = FakeDb([FakeResult(scalar_one_or_none=None)])
    assert await record_p4_feedback(1, db) is None


@pytest.mark.asyncio
async def test_intervention_missing_date_returns_none():
    itv = SimpleNamespace(id=1, date_intervention=None, machine_id=5)
    db = FakeDb([FakeResult(scalar_one_or_none=itv)])
    assert await record_p4_feedback(1, db) is None


@pytest.mark.asyncio
async def test_no_matching_flag_in_window_returns_none():
    now = datetime.now(timezone.utc)
    itv = SimpleNamespace(id=1, date_intervention=now, machine_id=5)
    db = FakeDb([
        FakeResult(scalar_one_or_none=itv),
        FakeResult(scalar_one_or_none=None),
    ])
    assert await record_p4_feedback(1, db) is None
    assert db.committed == 0


@pytest.mark.asyncio
async def test_success_records_outcome_and_commits():
    now = datetime.now(timezone.utc)
    itv = SimpleNamespace(id=1, date_intervention=now, machine_id=5)
    flag_log = SimpleNamespace(id=99, created_at=now - timedelta(days=2), p4_wo_outcome=None)
    db = FakeDb([
        FakeResult(scalar_one_or_none=itv),
        FakeResult(scalar_one_or_none=flag_log),
    ])
    result = await record_p4_feedback(1, db)
    assert result["flag_preceded_wo"] is True
    assert result["intervention_id"] == 1
    assert result["days_between"] == pytest.approx(2.0, abs=0.1)
    assert flag_log.p4_wo_outcome is not None
    assert db.committed == 1


@pytest.mark.asyncio
async def test_custom_window_days_passed_through():
    now = datetime.now(timezone.utc)
    itv = SimpleNamespace(id=1, date_intervention=now, machine_id=5)
    flag_log = SimpleNamespace(id=99, created_at=now - timedelta(days=1), p4_wo_outcome=None)
    db = FakeDb([
        FakeResult(scalar_one_or_none=itv),
        FakeResult(scalar_one_or_none=flag_log),
    ])
    result = await record_p4_feedback(1, db, window_days=30)
    assert result["window_days"] == 30


@pytest.mark.asyncio
async def test_commit_failure_rolls_back_and_returns_none():
    now = datetime.now(timezone.utc)
    itv = SimpleNamespace(id=1, date_intervention=now, machine_id=5)
    flag_log = SimpleNamespace(id=99, created_at=now - timedelta(days=1), p4_wo_outcome=None)

    class _FailingDb(FakeDb):
        async def commit(self):
            raise RuntimeError("db down")

    db = _FailingDb([
        FakeResult(scalar_one_or_none=itv),
        FakeResult(scalar_one_or_none=flag_log),
    ])
    result = await record_p4_feedback(1, db)
    assert result is None
    assert db.rolled_back == 1
