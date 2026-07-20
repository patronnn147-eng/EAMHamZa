"""Structural, no-DB tests — importing a SQLAlchemy model doesn't connect
to a database (core.database.Base only builds metadata at import time;
the engine is created lazily in DatabaseManager.init_db())."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app" / "backend"))

from models.machine_status_change_request import MachineStatusChangeRequest, RequestStatus


def test_tablename():
    assert MachineStatusChangeRequest.__tablename__ == "machine_status_change_requests"


def test_columns_present():
    columns = set(MachineStatusChangeRequest.__table__.columns.keys())
    expected = {
        "id", "machine_id", "from_status", "to_status", "status",
        "source_intervention_id", "requested_by", "requested_at",
        "reviewed_by", "reviewed_at", "review_note",
    }
    assert expected.issubset(columns)


def test_request_status_values():
    assert {s.value for s in RequestStatus} == {"PENDING", "APPROVED", "REJECTED"}


def test_status_column_default_is_pending():
    assert MachineStatusChangeRequest.__table__.c.status.default.arg == RequestStatus.PENDING


def test_status_column_is_not_native_enum():
    # native_enum=False is required — see Global Constraints. A native PG enum
    # here would break inserts the same way it would on OrdresTravail.statut.
    col_type = MachineStatusChangeRequest.__table__.c.status.type
    assert col_type.native_enum is False
