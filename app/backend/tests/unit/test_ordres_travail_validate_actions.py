"""Unit tests — the work-order /validate action vocabulary (no DB, no async).

Guards the fix for the unreachable-CLOSED gap: /close requires VALIDATED, but
before this fix nothing could ever set VALIDATED, so CLOSED was unreachable.
Source-level check because tests/unit/ has no async DB fixture."""
import ast
from pathlib import Path


def _validation_source() -> str:
    path = (
        Path(__file__).parent.parent.parent
        / "modules" / "shared" / "routes" / "ordres_travail" / "validation.py"
    )
    return path.read_text(encoding="utf-8-sig")


def test_validate_endpoint_supports_validate_action():
    src = _validation_source()
    assert '"VALIDATE"' in src, "validate endpoint must accept a VALIDATE action"
    assert "OrdreStatut.VALIDATED" in src, "VALIDATE action must set statut=VALIDATED"


def test_validation_module_parses():
    ast.parse(_validation_source())
