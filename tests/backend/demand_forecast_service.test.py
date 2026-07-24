"""Unit tests for app/backend/modules/ml/services/demand_forecast.py."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

import modules.ml.services.demand_forecast as df_mod
from modules.ml.services.demand_forecast import (
    _build_response,
    _days_until_stockout,
    _get_consumption_rates,
    _process_piece,
    _urgency_label,
    _urgency_score,
    compute_demand_forecast,
    invalidate_forecast_cache,
)


@pytest.fixture(autouse=True)
def _reset_cache():
    invalidate_forecast_cache()
    yield
    invalidate_forecast_cache()


# ── _urgency_score / _urgency_label ─────────────────────────────────────────

def test_urgency_score_high_when_rul_low_and_stock_low():
    score = _urgency_score(rul_days=1.0, failure_probability=90.0, current_qty=0, consumption_rate=2.0)
    assert score > 0.7


def test_urgency_score_low_when_healthy_and_well_stocked():
    score = _urgency_score(rul_days=90.0, failure_probability=0.0, current_qty=100, consumption_rate=1.0)
    assert score < 0.2


def test_urgency_score_clamped_to_unit_interval():
    score = _urgency_score(rul_days=-50.0, failure_probability=200.0, current_qty=-5, consumption_rate=1.0)
    assert 0.0 <= score <= 1.0


@pytest.mark.parametrize("score,expected", [(0.9, "URGENT"), (0.5, "SOON"), (0.1, "MONITOR")])
def test_urgency_label_thresholds(score, expected):
    assert _urgency_label(score) == expected


# ── _days_until_stockout ─────────────────────────────────────────────────────

def test_days_until_stockout_normal():
    assert _days_until_stockout(current_qty=30, consumption_rate_per_month=30.0) == 30


def test_days_until_stockout_zero_rate_returns_none():
    assert _days_until_stockout(current_qty=10, consumption_rate_per_month=0) is None


def test_days_until_stockout_negative_rate_returns_none():
    assert _days_until_stockout(current_qty=10, consumption_rate_per_month=-5) is None


# ── _get_consumption_rates ───────────────────────────────────────────────────

class FakeRatesResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class FakeDb:
    def __init__(self, execute_results=None):
        self._results = list(execute_results or [])

    async def execute(self, *_a, **_k):
        return self._results.pop(0)


@pytest.mark.asyncio
async def test_get_consumption_rates_computes_monthly_rate():
    now = datetime.now(timezone.utc)
    first_date = now - timedelta(days=90)
    db = FakeDb([FakeRatesResult([(1, 90.0, first_date, now)])])
    rates = await _get_consumption_rates(db)
    assert rates[1][0] == pytest.approx(30.0, rel=0.05)  # 90 units / 3 months
    assert rates[1][1] == "real"


@pytest.mark.asyncio
async def test_get_consumption_rates_skips_pieces_with_no_history():
    db = FakeDb([FakeRatesResult([(1, None, None, None), (2, 0, datetime.now(timezone.utc), datetime.now(timezone.utc))])])
    rates = await _get_consumption_rates(db)
    assert rates == {}


@pytest.mark.asyncio
async def test_get_consumption_rates_handles_naive_datetime():
    now = datetime.now(timezone.utc)
    naive_first_date = (now - timedelta(days=60)).replace(tzinfo=None)
    db = FakeDb([FakeRatesResult([(1, 60.0, naive_first_date, now)])])
    rates = await _get_consumption_rates(db)
    assert 1 in rates


# ── _process_piece ───────────────────────────────────────────────────────────

def test_process_piece_returns_none_when_piece_not_in_meta():
    result = _process_piece(99, [1], {}, {}, {}, {}, {})
    assert result is None


def test_process_piece_returns_none_when_no_machine_logs():
    piece_meta = {1: ("Belt", 5)}
    result = _process_piece(1, [10], piece_meta, {}, {}, {}, {})
    assert result is None


def test_process_piece_builds_forecast_item():
    piece_meta = {1: ("Belt", 5)}
    stock = {1: 2.0}
    rates = {1: (10.0, "real")}
    log = SimpleNamespace(rul_days=5.0, failure_probability=80.0)
    logs_by_machine = {10: log}
    machine_names = {10: "Press-1"}
    result = _process_piece(1, [10], piece_meta, stock, rates, logs_by_machine, machine_names)
    assert result["piece_id"] == 1
    assert result["urgency_label"] in ("URGENT", "SOON", "MONITOR")
    assert result["machines_affected"][0]["name"] == "Press-1"
    assert result["consumption_data"] == "real"


def test_process_piece_uses_horizon_default_when_rul_missing():
    piece_meta = {1: ("Belt", 5)}
    log = SimpleNamespace(rul_days=None, failure_probability=None)
    result = _process_piece(1, [10], piece_meta, {1: 5.0}, {}, {10: log}, {10: "M1"})
    assert result["machines_affected"][0]["rul_days"] == df_mod._RUL_HORIZON_DAYS


def test_process_piece_aggregates_max_urgency_across_machines():
    piece_meta = {1: ("Belt", 5)}
    low_log = SimpleNamespace(rul_days=90.0, failure_probability=0.0)
    high_log = SimpleNamespace(rul_days=1.0, failure_probability=95.0)
    result = _process_piece(
        1, [10, 20], piece_meta, {1: 0.0}, {1: (5.0, "real")},
        {10: low_log, 20: high_log}, {10: "M1", 20: "M2"},
    )
    # sorted descending by urgency -> highest-urgency machine first
    assert result["machines_affected"][0]["id"] == 20


# ── _build_response ──────────────────────────────────────────────────────────

def test_build_response_counts_by_label():
    items = [
        {"urgency_label": "URGENT"},
        {"urgency_label": "SOON"},
        {"urgency_label": "MONITOR"},
        {"urgency_label": "URGENT"},
    ]
    result = _build_response(items, horizon_days=60, ts=datetime.now(timezone.utc))
    assert result["total_urgent"] == 2
    assert result["total_monitor"] == 2
    assert result["items"] == items


# ── compute_demand_forecast ──────────────────────────────────────────────────

class FakeScalarsResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class FakeFetchResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


@pytest.mark.asyncio
async def test_compute_demand_forecast_no_piece_machine_links_returns_empty():
    db = FakeDb([
        FakeScalarsResult([]),   # latest logs
        FakeFetchResult([]),     # piece_machine links (empty)
    ])
    result = await compute_demand_forecast(db, horizon_days=60, limit=20)
    assert result["items"] == []
    assert result["total_urgent"] == 0


@pytest.mark.asyncio
async def test_compute_demand_forecast_returns_cached_data_when_fresh(monkeypatch):
    now = datetime.now(timezone.utc)
    df_mod._forecast_cache["data"] = {
        "_all_items": [
            {"piece_id": 1, "urgency_label": "URGENT", "machines_affected": [{"rul_days": 5}]},
        ],
        "generated_at": now.isoformat(),
    }
    df_mod._forecast_cache["timestamp"] = now

    db = FakeDb([])  # no execute calls expected — must hit cache
    result = await compute_demand_forecast(db, horizon_days=60, limit=20)
    assert result["items"][0]["piece_id"] == 1


@pytest.mark.asyncio
async def test_compute_demand_forecast_full_flow(monkeypatch):
    log = SimpleNamespace(machine_id=10, rul_days=5.0, failure_probability=80.0)
    db = FakeDb([
        FakeScalarsResult([log]),                    # latest logs per machine
        FakeFetchResult([(1, 10)]),                  # piece_machine links
        FakeFetchResult([(1, 2.0)]),                 # stock levels
        FakeFetchResult([(1, "Belt", 5)]),           # piece metadata
        FakeFetchResult([]),                         # consumption rates (mouvement_stock)
        FakeFetchResult([(10, "Press-1")]),          # machine names
    ])
    result = await compute_demand_forecast(db, horizon_days=60, limit=20)
    assert result["items"][0]["piece_id"] == 1
    assert result["items"][0]["machines_affected"][0]["name"] == "Press-1"


# ── invalidate_forecast_cache ─────────────────────────────────────────────────

def test_invalidate_forecast_cache_clears_state():
    df_mod._forecast_cache["data"] = {"x": 1}
    df_mod._forecast_cache["timestamp"] = datetime.now(timezone.utc)
    invalidate_forecast_cache()
    assert df_mod._forecast_cache["data"] is None
    assert df_mod._forecast_cache["timestamp"] is None
