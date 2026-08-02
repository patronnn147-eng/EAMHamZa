"""Unit tests — OrdresTravailResponse name-enrichment fields (no DB, no async)."""
from datetime import datetime, timezone

from modules.shared.routes.ordres_travail.schemas import OrdresTravailResponse


def _base_row(**overrides) -> dict:
    base = {
        "id": 1,
        "titre": "OT-TEST",
        "description": "desc",
        "priorite": "MOYENNE",
        "machine_id": 1,
        "statut": "CLOSED",
        "created_at": datetime.now(timezone.utc),
    }
    return {**base, **overrides}


def test_ordres_travail_response_defaults_names_to_none():
    resp = OrdresTravailResponse(**_base_row())
    assert resp.utilisateur_nom is None
    assert resp.validated_by_nom is None


def test_ordres_travail_response_accepts_resolved_names():
    resp = OrdresTravailResponse(
        **_base_row(utilisateur_nom="Karim Ben Ali", validated_by_nom="Sami Trabelsi")
    )
    assert resp.utilisateur_nom == "Karim Ben Ali"
    assert resp.validated_by_nom == "Sami Trabelsi"
