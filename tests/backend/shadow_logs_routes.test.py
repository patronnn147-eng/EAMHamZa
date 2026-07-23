"""Unit tests for app/backend/modules/ml/routes/shadow_logs.py route handlers,
called directly with a fake AsyncSession (bypassing FastAPI/HTTP)."""
import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from modules.ml.routes.shadow_logs import (
    get_anomaly_review_queue,
    get_p7_feedback_report,
    get_shadow_logs,
    submit_anomaly_verdict,
)


class FakeScalarsResult:
    def __init__(self, rows, total=None):
        self._rows = rows
        self._total = total if total is not None else len(rows)

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def scalar_one(self):
        return self._total

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class FakeDb:
    def __init__(self, execute_results):
        self._results = list(execute_results)
        self.committed = 0

    async def execute(self, *_a, **_k):
        return self._results.pop(0)

    async def commit(self):
        self.committed += 1


def _log(**overrides):
    base = dict(
        id=1, machine_id=1, machine_name="M1", risk_level="LOW", failure_probability=10.0,
        rul_days=30.0, predicted_failure_date=None, predicted_priority="P2", is_anomaly=False,
        anomaly_score=0.1, data_points=5, ml_model_used=True, created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


# ── get_shadow_logs ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_shadow_logs_paginates_and_serialises():
    db = FakeDb([FakeScalarsResult([], total=42), FakeScalarsResult([_log()])])
    result = await get_shadow_logs(page=1, size=100, machine_id=None, risk_level=None, db=db)
    assert result.total == 42
    assert result.items[0]["machine_name"] == "M1"
    assert result.items[0]["created_at"] == "2026-01-01T00:00:00+00:00"


@pytest.mark.asyncio
async def test_get_shadow_logs_handles_null_created_at():
    db = FakeDb([FakeScalarsResult([], total=1), FakeScalarsResult([_log(created_at=None)])])
    result = await get_shadow_logs(page=1, size=100, machine_id=None, risk_level=None, db=db)
    assert result.items[0]["created_at"] is None


# ── get_anomaly_review_queue ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_anomaly_review_queue_builds_sensor_snapshot():
    log = _log(
        id=2, is_anomaly=True, anomaly_score=0.9,
        air_temperature=300.0, process_temperature=310.0, rotational_speed=1500,
        torque=40.0, tool_wear=10.0,
    )
    db = FakeDb([FakeScalarsResult([log])])
    result = await get_anomaly_review_queue(limit=50, db=db)
    assert result["pending_count"] == 1
    assert result["items"][0]["sensor_snapshot"]["air_temperature"] == 300.0
    assert result["items"][0]["flagged_at"] == "2026-01-01T00:00:00+00:00"


@pytest.mark.asyncio
async def test_get_anomaly_review_queue_empty():
    db = FakeDb([FakeScalarsResult([])])
    result = await get_anomaly_review_queue(limit=50, db=db)
    assert result == {"pending_count": 0, "items": []}


# ── submit_anomaly_verdict ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_anomaly_verdict_invalid_verdict_raises_400():
    data = SimpleNamespace(verdict="NOT_A_VERDICT", root_cause_if_found=None)
    with pytest.raises(HTTPException) as exc_info:
        await submit_anomaly_verdict(1, data, db=FakeDb([]), current_user=SimpleNamespace(id=1))
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_submit_anomaly_verdict_log_not_found_raises_404():
    data = SimpleNamespace(verdict="CONFIRMED", root_cause_if_found=None)
    db = FakeDb([FakeScalarsResult([])])
    with pytest.raises(HTTPException) as exc_info:
        await submit_anomaly_verdict(1, data, db=db, current_user=SimpleNamespace(id=1))
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_submit_anomaly_verdict_success_updates_log():
    log = _log(id=5)
    data = SimpleNamespace(verdict="FALSE_POSITIVE", root_cause_if_found="sensor drift")
    db = FakeDb([FakeScalarsResult([log])])
    result = await submit_anomaly_verdict(5, data, db=db, current_user=SimpleNamespace(id=7))
    assert log.anomaly_verdict == "FALSE_POSITIVE"
    assert log.anomaly_root_cause == "sensor drift"
    assert log.anomaly_reviewed_by == 7
    assert db.committed == 1
    assert result["id"] == 5


# ── get_p7_feedback_report ─────────────────────────────────────────────────────

def _feedback_log(tp, predicted, actual, machine_id=1):
    payload = json.dumps({
        "_feedback": {"tp": tp, "predicted_count": predicted, "actual_count": actual, "precision": None, "recall": None},
    })
    return SimpleNamespace(p7_parts_demand=payload, machine_id=machine_id)


@pytest.mark.asyncio
async def test_p7_feedback_report_no_logs_returns_note():
    db = FakeDb([FakeScalarsResult([])])
    result = await get_p7_feedback_report(db)
    assert result["sample_count"] == 0
    assert result["precision"] is None
    assert "No feedback recorded" in result["note"]


@pytest.mark.asyncio
async def test_p7_feedback_report_micro_averages_across_interventions():
    logs = [_feedback_log(tp=2, predicted=4, actual=5), _feedback_log(tp=3, predicted=6, actual=5)]
    db = FakeDb([FakeScalarsResult(logs)])
    result = await get_p7_feedback_report(db)
    assert result["sample_count"] == 2
    assert result["precision"] == round(5 / 10, 4)  # (2+3)/(4+6)
    assert result["recall"] == round(5 / 10, 4)  # (2+3)/(5+5)
    assert result["f1"] is not None
    assert result["note"] is None


@pytest.mark.asyncio
async def test_p7_feedback_report_skips_legacy_entries_without_counts():
    legacy = SimpleNamespace(p7_parts_demand=json.dumps({"_feedback": {"precision": 0.5}}), machine_id=1)
    good = _feedback_log(tp=1, predicted=2, actual=2)
    db = FakeDb([FakeScalarsResult([legacy, good])])
    result = await get_p7_feedback_report(db)
    assert result["skipped_legacy_entries"] == 1
    assert result["sample_count"] == 1


@pytest.mark.asyncio
async def test_p7_feedback_report_skips_malformed_json():
    bad = SimpleNamespace(p7_parts_demand="not json", machine_id=1)
    good = _feedback_log(tp=1, predicted=1, actual=1)
    db = FakeDb([FakeScalarsResult([bad, good])])
    result = await get_p7_feedback_report(db)
    assert result["sample_count"] == 1


@pytest.mark.asyncio
async def test_p7_feedback_report_no_feedback_key_is_ignored():
    no_fb = SimpleNamespace(p7_parts_demand=json.dumps({"items": []}), machine_id=1)
    db = FakeDb([FakeScalarsResult([no_fb])])
    result = await get_p7_feedback_report(db)
    assert result["sample_count"] == 0
