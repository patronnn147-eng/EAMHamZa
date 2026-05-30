"""T27 — P7 feedback pure-function tests (no DB, no async)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app" / "backend"))

from modules.ml.services.p7_feedback import (
    parse_parts_demand_json,
    extract_predicted_names,
    extract_actual_names,
    compute_feedback_metrics,
)

_DEMAND = {
    "horizon_days": 30, "source": "p7_model",
    "items": [
        {"piece_id": 1, "name": "foret carbure", "shortfall": 1.0, "driver": "condition"},
        {"piece_id": 2, "name": "joint torique",  "shortfall": 0.0, "driver": "condition"},
    ]
}
_DEMAND_JSON = '{"horizon_days": 30, "source": "p7_model", "items": [{"piece_id": 1, "name": "foret carbure"}, {"piece_id": 2, "name": "joint torique"}]}'


# ── parse_parts_demand_json ───────────────────────────────────────────────

def test_parse_valid_json():
    result = parse_parts_demand_json(_DEMAND_JSON)
    assert result is not None
    assert result["source"] == "p7_model"

def test_parse_none_returns_none():
    assert parse_parts_demand_json(None) is None

def test_parse_invalid_json_returns_none():
    assert parse_parts_demand_json("not json!!!") is None


# ── extract_predicted_names ───────────────────────────────────────────────

def test_extract_predicted_names_from_demand():
    names = extract_predicted_names(_DEMAND)
    assert "foret carbure" in names
    assert "joint torique" in names

def test_extract_predicted_none_returns_empty():
    assert extract_predicted_names(None) == set()


# ── extract_actual_names ─────────────────────────────────────────────────

def test_extract_actual_strips_refs():
    text = "Tête de perçage complète (réf. TPC-6269), Bague d'étanchéité"
    names = extract_actual_names(text)
    assert any("perçage" in n or "percage" in n or "ete" in n for n in names), f"got: {names}"

def test_extract_actual_strips_sizes():
    text = "Roulements à billes 6305-ZZ x2, Ventilateur axial 120mm"
    names = extract_actual_names(text)
    assert any("roulement" in n for n in names)
    assert any("ventilateur" in n for n in names)

def test_extract_actual_none_returns_empty():
    assert extract_actual_names(None) == set()


# ── compute_feedback_metrics ──────────────────────────────────────────────

def test_perfect_match():
    m = compute_feedback_metrics({"a", "b"}, {"a", "b"})
    assert m["precision"] == 1.0
    assert m["recall"]    == 1.0
    assert m["f1"]        == 1.0

def test_zero_recall():
    m = compute_feedback_metrics({"x"}, {"a", "b"})
    assert m["recall"] == 0.0
    assert m["precision"] == 0.0

def test_partial_match():
    m = compute_feedback_metrics({"a", "b"}, {"a", "c"})
    assert 0 < m["precision"] < 1
    assert 0 < m["recall"] < 1
    assert m["tp"] == 1

def test_both_empty():
    m = compute_feedback_metrics(set(), set())
    assert m["precision"] is None
    assert m["recall"]    is None

def test_no_predictions():
    m = compute_feedback_metrics(set(), {"a"})
    assert m["precision"] is None
    assert m["recall"] == 0.0
