"""Unit tests — cheftech InterventionResponse technician-name fields (no DB, no async)."""
from datetime import datetime, timezone

from modules.cheftech.schemas import InterventionResponse


def _base(**overrides) -> dict:
    base = {"id": 1, "date_intervention": datetime.now(timezone.utc)}
    return {**base, **overrides}


def test_intervention_response_uses_technician_id_matching_orm_attribute():
    """Field must be named technician_id (matches OrdresIntervention.technician_id),
    not technicien_id — the old name never matched the ORM attribute and always
    serialized as None."""
    resp = InterventionResponse(**_base(technician_id=7))
    assert resp.technician_id == 7


def test_intervention_response_accepts_resolved_names():
    resp = InterventionResponse(
        **_base(technician_id=7, technicien_nom="Karim Ben Ali", approved_by=3, approved_by_nom="Sami Trabelsi")
    )
    assert resp.technicien_nom == "Karim Ben Ali"
    assert resp.approved_by_nom == "Sami Trabelsi"
