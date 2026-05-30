import json
from typing import Dict, Optional
from models.ml_prediction_log import MlPredictionLog


class ShadowLogger:

    @staticmethod
    def _serialise_parts_demand(parts_demand: Optional[Dict]) -> Optional[str]:
        """Serialise parts_demand contract to JSON string for Text column."""
        if not parts_demand:
            return None
        try:
            return json.dumps(parts_demand, default=str)
        except Exception:
            return None

    @staticmethod
    def create_shadow_log(prediction: Dict) -> MlPredictionLog:
        """
        Create an MlPredictionLog object from a prediction dictionary.
        This is used for PDCA Shadow Logging (Phase 1 + P7 extension).
        The caller (router) is responsible for adding & committing to the DB session.
        """
        p7_json = ShadowLogger._serialise_parts_demand(
            prediction.get("p7_parts_demand")
        )
        return MlPredictionLog(
            machine_id=prediction.get("machine_id"),
            machine_name=prediction.get("machine_name"),
            risk_level=prediction.get("risk_level"),
            failure_probability=prediction.get("failure_probability"),
            rul_days=prediction.get("rul_days"),
            predicted_failure_date=prediction.get("predicted_failure_date"),
            predicted_priority=prediction.get("predicted_priority"),
            is_anomaly=prediction.get("is_anomaly", False),
            anomaly_score=prediction.get("anomaly_score", 0.0),
            data_points=prediction.get("data_points"),
            ml_model_used=prediction.get("ml_model_used", False),
            air_temperature=prediction.get("air_temperature"),
            process_temperature=prediction.get("process_temperature"),
            rotational_speed=prediction.get("rotational_speed"),
            torque=prediction.get("torque"),
            tool_wear=prediction.get("tool_wear"),
            p7_parts_demand=p7_json,
        )
