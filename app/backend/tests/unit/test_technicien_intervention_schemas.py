"""Unit tests — technicien InterventionResponse approved_by_nom field (no DB, no async)."""
from datetime import datetime, timezone

from modules.technicien.schemas import InterventionResponse


def test_intervention_response_accepts_approved_by_nom():
    resp = InterventionResponse(
        id=1, statut="EN_ATTENTE", date_intervention=datetime.now(timezone.utc),
        approved_by=3, approved_by_nom="Sami Trabelsi",
    )
    assert resp.approved_by_nom == "Sami Trabelsi"


def test_intervention_response_defaults_approved_by_nom_to_none():
    resp = InterventionResponse(id=1, statut="EN_ATTENTE", date_intervention=datetime.now(timezone.utc))
    assert resp.approved_by_nom is None
