"""T25/T26 — p7_parts_demand column exists in model + ShadowLogger persists it."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app" / "backend"))

# Import models in dependency order so SQLAlchemy resolves relationships
import models.alertes          # noqa: F401 — Alert must load before Utilisateurs resolves it
import models.utilisateurs      # noqa: F401
import models.ml_prediction_log # noqa: F401

from models.ml_prediction_log import MlPredictionLog
from modules.ml.logging import ShadowLogger


_PARTS_DEMAND = {
    "horizon_days": 30,
    "source": "p7_model",
    "items": [
        {"piece_id": 1, "name": "foret carbure", "expected_qty": 1.5,
         "on_hand": 0, "shortfall": 1.5, "urgency_score": 1.0,
         "recommended_order_qty": 2.0, "driver": "condition"}
    ]
}


def test_ml_prediction_log_has_p7_column():
    """Model column exists."""
    assert hasattr(MlPredictionLog, "p7_parts_demand")


def test_shadow_logger_serialises_p7_parts_demand():
    prediction = {
        "machine_id": 42,
        "risk_level": "HIGH",
        "failure_probability": 75.0,
        "rul_days": 12.0,
        "is_anomaly": False,
        "anomaly_score": 0.3,
        "p7_parts_demand": _PARTS_DEMAND,
    }
    log = ShadowLogger.create_shadow_log(prediction)
    assert log.p7_parts_demand is not None
    parsed = json.loads(log.p7_parts_demand)
    assert parsed["source"] == "p7_model"
    assert parsed["horizon_days"] == 30
    assert len(parsed["items"]) == 1
    assert parsed["items"][0]["piece_id"] == 1


def test_shadow_logger_none_when_no_p7():
    log = ShadowLogger.create_shadow_log({"machine_id": 1, "risk_level": "LOW"})
    assert log.p7_parts_demand is None


def test_shadow_logger_none_when_p7_is_none():
    log = ShadowLogger.create_shadow_log({"machine_id": 1, "p7_parts_demand": None})
    assert log.p7_parts_demand is None


def test_serialise_preserves_all_contract_keys():
    log = ShadowLogger.create_shadow_log({"machine_id": 1, "p7_parts_demand": _PARTS_DEMAND})
    parsed = json.loads(log.p7_parts_demand)
    item = parsed["items"][0]
    for key in ("piece_id", "name", "expected_qty", "on_hand", "shortfall",
                "urgency_score", "recommended_order_qty", "driver"):
        assert key in item, f"missing key in stored item: {key}"
