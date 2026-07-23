"""Unit tests for the P7 KPI/queue route handlers in
app/backend/modules/ml/routes/procurement.py, called directly (bypassing
FastAPI/HTTP) with a fake AsyncSession."""
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from modules.ml.routes.procurement import get_p7_kpis, get_procurement_queue


class FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value

    def all(self):
        return self._value


class FakeDb:
    def __init__(self, execute_results):
        self._results = list(execute_results)

    async def execute(self, *_a, **_k):
        return self._results.pop(0)


# ── get_p7_kpis ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_p7_kpis_computes_rates():
    db = FakeDb([
        FakeScalarResult(10),  # total_machines
        FakeScalarResult(2),   # shortage_count
        FakeScalarResult(7),   # predicted_machines
        FakeScalarResult(3),   # draft_count
    ])
    result = await get_p7_kpis(db)
    kpis = result["kpis"]
    assert kpis["stock_readiness_rate"] == 80.0  # (10-2)/10 * 100
    assert kpis["adoption_rate"] == 70.0  # 7/10 * 100
    assert kpis["active_shortages"] == 2
    assert kpis["draft_wos_pending"] == 3
    assert kpis["total_machines"] == 10


@pytest.mark.asyncio
async def test_get_p7_kpis_avoids_division_by_zero_with_no_machines():
    db = FakeDb([
        FakeScalarResult(None),  # total_machines -> defaults to 1 via `or 1`
        FakeScalarResult(0),
        FakeScalarResult(0),
        FakeScalarResult(0),
    ])
    result = await get_p7_kpis(db)
    assert result["kpis"]["total_machines"] == 1
    assert result["kpis"]["stock_readiness_rate"] == 100.0


# ── get_procurement_queue ─────────────────────────────────────────────────────

class _Row:
    def __init__(self, alert, machine):
        self.Alert = alert
        self.Machines = machine


@pytest.mark.asyncio
async def test_get_procurement_queue_maps_joined_rows():
    alert = SimpleNamespace(
        alert_id=1, machine_id=5, severity=SimpleNamespace(value="HIGH"),
        message="Low stock", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    machine = SimpleNamespace(nom="M5")
    db = FakeDb([FakeScalarResult([_Row(alert, machine)])])
    result = await get_procurement_queue(db)
    assert result["success"] is True
    assert result["count"] == 1
    assert result["items"][0]["machine_name"] == "M5"
    assert result["items"][0]["severity"] == "HIGH"
    assert result["items"][0]["created_at"] == "2026-01-01T00:00:00+00:00"


@pytest.mark.asyncio
async def test_get_procurement_queue_empty():
    db = FakeDb([FakeScalarResult([])])
    result = await get_procurement_queue(db)
    assert result == {"success": True, "count": 0, "items": []}


@pytest.mark.asyncio
async def test_get_procurement_queue_null_created_at():
    alert = SimpleNamespace(
        alert_id=1, machine_id=5, severity=SimpleNamespace(value="LOW"),
        message="msg", created_at=None,
    )
    machine = SimpleNamespace(nom="M5")
    db = FakeDb([FakeScalarResult([_Row(alert, machine)])])
    result = await get_procurement_queue(db)
    assert result["items"][0]["created_at"] is None
