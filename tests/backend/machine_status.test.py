"""Pure, no-DB tests for the shared machine-status vocabulary."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app" / "backend"))

from models.machine_status import MACHINE_STATUSES, is_valid_machine_status


def test_machine_statuses_has_five_values():
    assert len(MACHINE_STATUSES) == 5


def test_fonctionnement_restreint_included():
    assert "FONCTIONNEMENT_RESTREINT" in MACHINE_STATUSES


def test_existing_four_statuses_preserved():
    for value in ("OPERATIONNELLE", "EN_MAINTENANCE", "EN_PANNE", "HORS_SERVICE"):
        assert value in MACHINE_STATUSES


def test_is_valid_machine_status_true_for_known_value():
    assert is_valid_machine_status("OPERATIONNELLE") is True


def test_is_valid_machine_status_false_for_unknown_value():
    assert is_valid_machine_status("ACTIF") is False


def test_is_valid_machine_status_false_for_none_semantics_not_applicable():
    # is_valid_machine_status expects a str; callers guard None themselves
    # (see Task 7/8 validators) — this just documents empty string is invalid.
    assert is_valid_machine_status("") is False
