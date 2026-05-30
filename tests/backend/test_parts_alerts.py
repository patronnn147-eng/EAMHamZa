"""
T11 — parts_alerts pure-function tests (no DB, no async).
Tests extract_shortage_items, _build_shortage_message, _determine_severity.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app" / "backend"))

from modules.ml.services.parts_alerts import (
    extract_shortage_items,
    _build_shortage_message,
    _determine_severity,
)
from models.alertes import AlertSeverity


# ── extract_shortage_items ─────────────────────────────────────────────────

def test_extract_shortage_items_returns_only_shortfall():
    demand = {
        "source": "p7_model",
        "horizon_days": 30,
        "items": [
            {"piece_id": 1, "name": "foret carbure", "shortfall": 1.5, "driver": "condition"},
            {"piece_id": 2, "name": "huile",          "shortfall": 0.0, "driver": "consumption"},
            {"piece_id": 3, "name": "joint torique",  "shortfall": 0.8, "driver": "condition"},
        ],
    }
    result = extract_shortage_items(demand)
    assert len(result) == 2
    assert all(i["shortfall"] > 0 for i in result)


def test_extract_shortage_items_empty_when_no_shortfall():
    demand = {"source": "p7_model", "horizon_days": 30, "items": [
        {"piece_id": 1, "name": "roulement", "shortfall": 0.0, "driver": "condition"},
    ]}
    assert extract_shortage_items(demand) == []


def test_extract_shortage_items_returns_empty_on_none():
    assert extract_shortage_items(None) == []


def test_extract_shortage_items_returns_empty_on_fallback():
    demand = {"source": "deterministic_fallback", "horizon_days": 30, "items": []}
    assert extract_shortage_items(demand) == []


# ── _build_shortage_message ────────────────────────────────────────────────

def test_build_message_lists_top_3_parts():
    items = [
        {"piece_id": i, "name": f"part {i}", "shortfall": 1.0, "driver": "condition"}
        for i in range(5)
    ]
    msg = _build_shortage_message(items)
    assert "part 0" in msg.lower()
    assert "(+2 more)" in msg


def test_build_message_single_part():
    items = [{"piece_id": 1, "name": "foret carbure", "shortfall": 1.0, "driver": "condition"}]
    msg = _build_shortage_message(items)
    assert "foret carbure" in msg.lower()
    assert "more" not in msg


# ── _determine_severity ────────────────────────────────────────────────────

def test_severity_critical_when_condition_driver():
    items = [{"shortfall": 1.0, "driver": "condition"}]
    assert _determine_severity(items) == AlertSeverity.CRITICAL


def test_severity_high_when_consumption_only():
    items = [{"shortfall": 1.0, "driver": "consumption"}]
    assert _determine_severity(items) == AlertSeverity.HIGH


def test_severity_critical_if_any_condition():
    items = [
        {"shortfall": 0.5, "driver": "consumption"},
        {"shortfall": 1.0, "driver": "condition"},
    ]
    assert _determine_severity(items) == AlertSeverity.CRITICAL
