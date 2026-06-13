"""Quick Action plan-builder tests (pure, no DB)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app" / "backend"))

from modules.ml.services.quick_action import build_execution_plan


def _piece(pid, ref, name, min_stock=5, is_consumable=False):
    return {"id": pid, "reference": ref, "name": name,
            "min_stock": min_stock, "is_consumable": is_consumable, "default_unit": "pcs"}


def test_resolve_by_piece_id_existing():
    items = [{"piece_id": 10, "reference": "X", "name": "Bearing",
              "expected_qty": 2.0, "recommended_order_qty": 2.0, "driver": "condition"}]
    pieces_by_id = {10: _piece(10, "B-10", "Bearing")}
    plan = build_execution_plan(items, 1, pieces_by_id, {}, {}, stock_by_piece_id={})
    op = plan["ops"][0]
    assert op["resolution"] == "id"
    assert op["action"] == "existing"
    assert op["piece_id"] == 10
    # target = max(2, min_stock 5) = 5; on_hand 0 -> delta 5
    assert op["target_qty"] == 5
    assert op["qty_added"] == 5
    assert op["stock_action"] == "added"
    assert plan["summary"]["pieces_existing"] == 1
    assert plan["summary"]["stock_updated"] == 1
    assert plan["summary"]["total_qty_added"] == 5


def test_bad_piece_id_falls_through_to_reference():
    items = [{"piece_id": 999, "reference": "REF-A", "name": "Seal",
              "expected_qty": 1.0, "recommended_order_qty": 1.0, "driver": "consumption"}]
    pieces_by_ref = {"REF-A": _piece(3, "REF-A", "Seal", min_stock=0, is_consumable=True)}
    plan = build_execution_plan(items, 1, {}, pieces_by_ref, {}, stock_by_piece_id={3: 0.0})
    op = plan["ops"][0]
    assert op["resolution"] == "reference"
    assert op["piece_id"] == 3
    assert op["target_qty"] == 1.0      # consumable keeps decimal
    assert op["qty_added"] == 1.0


def test_resolve_by_name_case_insensitive():
    items = [{"piece_id": None, "reference": None, "name": "Foret Carbure",
              "expected_qty": 3.0, "recommended_order_qty": 3.0, "driver": "condition"}]
    pieces_by_lname = {"foret carbure": _piece(7, "FC-7", "Foret Carbure", min_stock=0)}
    plan = build_execution_plan(items, 1, {}, {}, pieces_by_lname, stock_by_piece_id={7: 1.0})
    op = plan["ops"][0]
    assert op["resolution"] == "name"
    assert op["piece_id"] == 7
    assert op["target_qty"] == 3        # ceil(max(3,0))
    assert op["qty_added"] == 2         # 3 target - 1 on_hand


def test_create_when_unresolved():
    items = [{"piece_id": None, "reference": None, "name": "New Valve",
              "expected_qty": 2.4, "recommended_order_qty": 2.4, "driver": "condition"}]
    plan = build_execution_plan(items, 42, {}, {}, {}, stock_by_piece_id={})
    op = plan["ops"][0]
    assert op["resolution"] == "create"
    assert op["action"] == "created"
    assert op["piece_id"] is None                     # DB assigns later
    assert op["reference"].startswith("QA-42-new-valve-")
    assert op["create_spec"]["min_stock"] == 3        # ceil(2.4)
    assert op["create_spec"]["category"] == "Predictive"
    assert op["create_spec"]["is_consumable"] is False
    assert op["target_qty"] == 3                       # ceil(max(2.4, 3))
    assert op["qty_added"] == 3
    assert plan["summary"]["pieces_created"] == 1


def test_skip_when_stock_already_covers_target():
    items = [{"piece_id": 10, "reference": "X", "name": "Bearing",
              "expected_qty": 2.0, "recommended_order_qty": 2.0, "driver": "condition"}]
    pieces_by_id = {10: _piece(10, "B-10", "Bearing", min_stock=5)}
    plan = build_execution_plan(items, 1, pieces_by_id, {}, {}, stock_by_piece_id={10: 9.0})
    op = plan["ops"][0]
    assert op["stock_action"] == "skipped"
    assert op["qty_added"] == 0
    assert plan["summary"]["skipped"] == 1
    assert plan["summary"]["stock_updated"] == 0


def test_intra_run_duplicate_creates_one_piece():
    # Two items, same name, neither resolves -> must create ONE piece, not two.
    items = [
        {"piece_id": None, "reference": None, "name": "Gasket",
         "expected_qty": 2.0, "recommended_order_qty": 2.0, "driver": "condition"},
        {"piece_id": None, "reference": None, "name": "gasket",
         "expected_qty": 4.0, "recommended_order_qty": 4.0, "driver": "condition"},
    ]
    plan = build_execution_plan(items, 1, {}, {}, {}, stock_by_piece_id={})
    creates = [o for o in plan["ops"] if o["resolution"] == "create"]
    assert len(creates) == 1                  # deduped within the run
    assert creates[0]["target_qty"] == 4      # max(2,4) ceil
    assert plan["summary"]["pieces_created"] == 1
