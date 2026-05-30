"""T18 — parts_drafts pure-function tests (no DB, no async)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app" / "backend"))

from modules.ml.services.parts_drafts import (
    _determine_priority,
    _build_wo_title,
    _build_wo_description,
)

_CONDITION_ITEM = {"piece_id": 1, "name": "foret carbure", "expected_qty": 2.0,
                   "on_hand": 0, "shortfall": 2.0, "driver": "condition"}
_CONSUMPTION_ITEM = {"piece_id": 2, "name": "huile", "expected_qty": 1.0,
                     "on_hand": 0, "shortfall": 1.0, "driver": "consumption"}
_INSTOCK_ITEM = {"piece_id": 3, "name": "joint", "expected_qty": 0.5,
                 "on_hand": 5, "shortfall": 0.0, "driver": "condition"}


# ── _determine_priority ───────────────────────────────────────────────────

def test_priority_urgente_on_condition_shortfall():
    assert _determine_priority([_CONDITION_ITEM]) == "URGENTE"

def test_priority_elevee_on_consumption_only():
    assert _determine_priority([_CONSUMPTION_ITEM]) == "ÉLEVÉE"

def test_priority_moyenne_on_no_shortfall():
    assert _determine_priority([_INSTOCK_ITEM]) == "MOYENNE"

def test_priority_urgente_mixed_condition_wins():
    assert _determine_priority([_CONSUMPTION_ITEM, _CONDITION_ITEM]) == "URGENTE"


# ── _build_wo_title ───────────────────────────────────────────────────────

def test_wo_title_contains_machine_id():
    title = _build_wo_title(42)
    assert "42" in title
    assert "[P7]" in title


# ── _build_wo_description ─────────────────────────────────────────────────

def test_wo_description_lists_parts():
    demand = {"horizon_days": 30, "source": "p7_model",
              "items": [_CONDITION_ITEM, _INSTOCK_ITEM]}
    desc = _build_wo_description(demand)
    assert "foret carbure" in desc.lower()
    assert "ORDER" in desc          # shortage item flagged for order
    assert "30 days" in desc


def test_wo_description_human_approval_notice():
    demand = {"horizon_days": 30, "source": "p7_model", "items": [_CONDITION_ITEM]}
    desc = _build_wo_description(demand)
    assert "Human approval required" in desc


def test_wo_description_no_jargon():
    demand = {"horizon_days": 30, "source": "p7_model", "items": [_CONDITION_ITEM]}
    desc = _build_wo_description(demand).lower()
    for banned in ("weibull", "croston", "isolation forest", "xgboost", "feature importance"):
        assert banned not in desc, f"Jargon found: {banned}"
