"""Unit tests — chetop WorkOrderResponse name-enrichment field (no DB, no async)."""
from datetime import datetime, timezone

from modules.chetop.schemas import WorkOrderResponse


def test_chetop_work_order_response_accepts_utilisateur_nom():
    resp = WorkOrderResponse(
        id=1, titre="OT", priorite="MOYENNE", statut="DRAFT", machine_id=1,
        created_at=datetime.now(timezone.utc), utilisateur_nom="Karim Ben Ali",
    )
    assert resp.utilisateur_nom == "Karim Ben Ali"


def test_chetop_work_order_response_defaults_utilisateur_nom_to_none():
    resp = WorkOrderResponse(
        id=1, titre="OT", priorite="MOYENNE", statut="DRAFT", machine_id=1,
        created_at=datetime.now(timezone.utc),
    )
    assert resp.utilisateur_nom is None
