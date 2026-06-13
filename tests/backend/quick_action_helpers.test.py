"""Quick Action pure-helper tests (no DB, no async)."""
import sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app" / "backend"))

from modules.ml.services.quick_action import (
    _slug, _short_hash, _execution_hash, _target_qty, _driver_to_category,
)


def test_slug_basic():
    assert _slug("Bearing 6204 ZZ") == "bearing-6204-zz"

def test_slug_collapses_and_trims():
    assert _slug("  Foret  Carbure!! ") == "foret-carbure"

def test_slug_empty_fallback():
    assert _slug("") == "part"
    assert _slug("***") == "part"

def test_short_hash_stable_and_6_chars():
    h1 = _short_hash("bearing", 42)
    h2 = _short_hash("bearing", 42)
    assert h1 == h2
    assert len(h1) == 6
    assert _short_hash("bearing", 43) != h1   # machine_id changes hash

def test_execution_hash_order_independent():
    a = [{"piece_id": 1, "reference": "R1", "name": "a", "expected_qty": 1.0,
          "recommended_order_qty": 1.0, "driver": "condition"},
         {"piece_id": 2, "reference": "R2", "name": "b", "expected_qty": 2.0,
          "recommended_order_qty": 2.0, "driver": "consumption"}]
    assert _execution_hash(list(reversed(a)), 7) == _execution_hash(a, 7)

def test_execution_hash_changes_with_machine_and_qty():
    items = [{"piece_id": 1, "reference": "R1", "name": "a", "expected_qty": 1.0,
              "recommended_order_qty": 1.0, "driver": "condition"}]
    base = _execution_hash(items, 7)
    assert _execution_hash(items, 8) != base
    items2 = [dict(items[0], expected_qty=9.0)]
    assert _execution_hash(items2, 7) != base

def test_target_qty_non_consumable_ceils():
    assert _target_qty(expected_qty=1.2, min_stock=0, is_consumable=False) == 2

def test_target_qty_uses_min_stock_floor():
    assert _target_qty(expected_qty=1.0, min_stock=5, is_consumable=False) == 5

def test_target_qty_consumable_keeps_decimal():
    assert _target_qty(expected_qty=1.25, min_stock=0, is_consumable=True) == 1.25

def test_driver_to_category():
    assert _driver_to_category("condition") == "Predictive"
    assert _driver_to_category("consumption") == "Consumable"
    assert _driver_to_category("anything-else") == "General"
