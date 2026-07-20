"""Pure test: pydantic validation only."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app" / "backend"))

import pytest
from pydantic import ValidationError
from modules.chetop.schemas import WorkOrderCompletePayload


def test_valid_machine_status_after_accepted():
    payload = WorkOrderCompletePayload(
        rapport="ok", machine_status_after="EN_PANNE"
    )
    assert payload.machine_status_after == "EN_PANNE"


def test_invalid_machine_status_after_rejected():
    with pytest.raises(ValidationError):
        WorkOrderCompletePayload(rapport="ok", machine_status_after="EN_MARCHE")


def test_none_machine_status_after_accepted():
    payload = WorkOrderCompletePayload(rapport="ok")
    assert payload.machine_status_after is None
