from typing import Dict
from models.ml_prediction_log import MlPredictionLog


class ShadowLogger:
    
    @staticmethod
    def create_shadow_log(prediction: Dict) -> MlPredictionLog:
        """
        Create an MlPredictionLog object from a prediction dictionary.
        This is used for PDCA Shadow Logging (Phase 1).
        The caller (router) is responsible for adding & committing to the DB session.
        """
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
            tool_wear=prediction.get("tool_wear")
        )
