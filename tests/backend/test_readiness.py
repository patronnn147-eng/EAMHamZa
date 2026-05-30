"""T21/T22 — readiness score + timeline pure-function tests."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app" / "backend"))

from modules.ml.services.readiness import compute_readiness_score, build_timeline_events

# ── compute_readiness_score ───────────────────────────────────────────────

def test_readiness_perfect_conditions():
    r = compute_readiness_score(
        unified_health_score=100.0,
        parts_shortage_active=False,
        parts_demand_items=[],
        days_since_last_maintenance=3.0,
    )
    assert r["readiness_score"] == 100.0


def test_readiness_worst_case():
    r = compute_readiness_score(
        unified_health_score=0.0,
        parts_shortage_active=True,
        parts_demand_items=[{"expected_qty": 5, "shortfall": 5}],
        days_since_last_maintenance=365.0,
    )
    assert r["readiness_score"] < 20.0


def test_readiness_shortage_penalty():
    r_no  = compute_readiness_score(100.0, False, [], None)
    r_yes = compute_readiness_score(100.0, True,  [], None)
    assert r_no["readiness_score"] > r_yes["readiness_score"]


def test_readiness_partial_inventory():
    items = [{"expected_qty": 4, "shortfall": 2}]
    r = compute_readiness_score(80.0, False, items, 14.0)
    assert 0 < r["readiness_score"] < 100


def test_readiness_breakdown_sums_to_total():
    r = compute_readiness_score(75.0, False, [{"expected_qty": 2, "shortfall": 1}], 20.0)
    bd = r["breakdown"]
    total = sum(bd.values())
    assert abs(total - r["readiness_score"]) < 0.1


def test_readiness_missing_health_uses_neutral():
    r = compute_readiness_score(None, False, [], None)
    # health defaults to 50, no shortage, no items, no recency → around 50*0.4 + 100*0.3 + 100*0.2 + 50*0.1
    assert 50 < r["readiness_score"] < 80


def test_readiness_score_clamped_0_100():
    r = compute_readiness_score(200.0, False, [], 0.0)
    assert 0 <= r["readiness_score"] <= 100


# ── build_timeline_events ─────────────────────────────────────────────────

from datetime import datetime, timezone

_T1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
_T2 = datetime(2026, 2, 1, tzinfo=timezone.utc)
_T3 = datetime(2026, 3, 1, tzinfo=timezone.utc)


def test_timeline_sorted_chronologically():
    events = build_timeline_events(
        prediction_log_rows=[{"created_at": _T3, "failure_probability": 70, "rul_days": 10}],
        work_order_rows=[{"id": 1, "titre": "WO1", "statut": "DRAFT",
                          "created_at": _T1, "date_validation": None,
                          "date_debut": None, "date_fin": None}],
        intervention_rows=[{"approved_at": _T2, "date_fin": None, "machine_category": "CMS"}],
        alert_rows=[],
    )
    dates = [e["date"] for e in events]
    assert dates == sorted(dates)


def test_timeline_skips_none_dates():
    events = build_timeline_events(
        prediction_log_rows=[{"created_at": None, "failure_probability": 0, "rul_days": None}],
        work_order_rows=[], intervention_rows=[], alert_rows=[],
    )
    assert events == []


def test_timeline_deduplicates():
    row = {"created_at": _T1, "failure_probability": 50, "rul_days": 30}
    events = build_timeline_events([row, row], [], [], [])
    types = [e["type"] for e in events]
    assert types.count("forecast") == 1


def test_timeline_event_has_required_keys():
    events = build_timeline_events(
        prediction_log_rows=[{"created_at": _T1, "failure_probability": 40, "rul_days": 20}],
        work_order_rows=[], intervention_rows=[], alert_rows=[],
    )
    assert len(events) == 1
    for key in ("date", "type", "label"):
        assert key in events[0]
