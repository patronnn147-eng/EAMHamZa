"""Pure test: pydantic validation only. Importing technicien_work_orders.py
pulls in its full dependency chain (routers, services) but does not touch
the DB at import time — same as importing modules.ml.router does elsewhere
in this codebase."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app" / "backend"))

import pytest
from pydantic import ValidationError
from modules.technicien.technicien_work_orders import WorkOrderCompletePayload


def test_valid_machine_status_after_accepted():
    payload = WorkOrderCompletePayload(
        rapport="ok", machine_status_after="FONCTIONNEMENT_RESTREINT"
    )
    assert payload.machine_status_after == "FONCTIONNEMENT_RESTREINT"


def test_invalid_machine_status_after_rejected():
    with pytest.raises(ValidationError):
        WorkOrderCompletePayload(rapport="ok", machine_status_after="BOGUS")


def test_none_machine_status_after_accepted():
    payload = WorkOrderCompletePayload(rapport="ok")
    assert payload.machine_status_after is None
