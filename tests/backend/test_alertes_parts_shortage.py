"""T10 — PARTS_SHORTAGE alert type exists in AlertType enum."""
from models.alertes import AlertType


def test_parts_shortage_in_alert_type():
    assert hasattr(AlertType, 'PARTS_SHORTAGE')
    assert AlertType.PARTS_SHORTAGE.value == 'PARTS_SHORTAGE'


def test_parts_shortage_value_usable_as_string():
    # .value is the string stored in the DB column
    assert AlertType.PARTS_SHORTAGE.value == 'PARTS_SHORTAGE'
    # enum member is equal to its string value (str mixin)
    assert AlertType.PARTS_SHORTAGE == 'PARTS_SHORTAGE'


def test_all_legacy_types_still_present():
    for name in ('RUL_WARNING', 'FAILURE_PREDICTED', 'ANOMALY_DETECTED'):
        assert hasattr(AlertType, name), f"Missing: {name}"
