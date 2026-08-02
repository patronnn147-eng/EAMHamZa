"""Confirms complete_work_order() calls both ML feedback hooks — a source-level
check because this repo's tests/unit/ has no async DB fixture to exercise the
route directly (see pytest.ini: testpaths = tests, no conftest under tests/unit/)."""
import ast
from pathlib import Path


def _get_function_source(file_path: Path, function_name: str) -> str:
    tree = ast.parse(file_path.read_text(encoding="utf-8-sig"))
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name:
            return ast.get_source_segment(file_path.read_text(encoding="utf-8-sig"), node)
    raise AssertionError(f"{function_name} not found in {file_path}")


def test_complete_work_order_calls_p7_and_p4_feedback():
    file_path = Path(__file__).parent.parent.parent / "modules" / "technicien" / "technicien_work_orders.py"
    source = _get_function_source(file_path, "complete_work_order")
    assert "record_p7_feedback(" in source, "complete_work_order must call record_p7_feedback"
    assert "record_p4_feedback(" in source, "complete_work_order must call record_p4_feedback"
