"""
ML Predictions Service
Provides P1-P6 prediction methods
"""
import numpy as np
from typing import List, Dict, Optional

from .model_loader import (
    get_model,
    _ml_model_p2,
    _ml_model_p3,
    _ml_model_p4,
    _ml_model_p5,
    _ml_model_p6,
    _p2_labels,
    _p5_labels,
)


class MachineLearningService:
    """Unified ML prediction service for all P1-P6 models."""

    # ==================== P1: Failure Probability ====================
    @staticmethod
    def predict_failure_probability(features: List[float]) -> float:
        """
        Predict failure probability using P1 model.
        Args: [air, process, rpm, torque, wear, temp_delta, rpm_torque] (7 features)
        Returns: probability (0-100)
        """
        model_p1 = get_model()
        if model_p1 is None:
            return 0.0
        try:
            # Ensure we have 7 features: [air, process, rpm, torque, wear, temp_delta, rpm_torque]
            air = float(features[0]) if len(features) > 0 else 298.0
            process = float(features[1]) if len(features) > 1 else 308.0
            rpm = float(features[2]) if len(features) > 2 else 1500.0
            torque = float(features[3]) if len(features) > 3 else 40.0
            wear = float(features[4]) if len(features) > 4 else 0.0
            
            # Add derived features if not provided
            temp_delta = float(features[5]) if len(features) > 5 else process - air
            rpm_torque = float(features[6]) if len(features) > 6 else (rpm * torque) / 1000.0
            
            features_7 = [air, process, rpm, torque, wear, temp_delta, rpm_torque]
            prob = model_p1.predict_proba([features_7])[0, 1]
            return round(prob * 100, 1)
        except Exception:
            return 0.0

    # ==================== P2: Failure Type ====================
    @staticmethod
    def predict_failure_type(features: List[float]) -> Dict:
        """
        Predict specific failure types using P2 model.
        Features: [air, process, rpm, torque, wear, temp_delta]
        Returns: {TWF: {detected, probability}, HDF: {...}, etc.}
        """
        if _ml_model_p2 is None:
            return {}

        input_data = [features]
        predictions = _ml_model_p2.predict(input_data)[0]
        probabilities = [est.predict_proba(input_data)[0, 1] for est in _ml_model_p2.estimators_]

        result = {}
        for i, label in enumerate(_p2_labels):
            result[label] = {
                "detected": bool(predictions[i]),
                "probability": round(float(probabilities[i]) * 100, 1)
            }

        return result

    # ==================== P3: RUL Estimation ====================
    @staticmethod
    def predict_rul(features: List[float]) -> Optional[float]:
        """
        Predict Remaining Useful Life using P3 XGBoost.
        Args: [air, process, rpm, torque, wear] (5 features)
        Returns: days until failure
        """
        if _ml_model_p3 is None:
            return None
        try:
            pred_rul = _ml_model_p3.predict(np.array([features]))[0]
            return float(pred_rul)
        except Exception:
            return None

    # ==================== P4: Anomaly Detection ====================
    @staticmethod
    def detect_anomaly(features: List[float]) -> tuple:
        """
        Detect machine anomaly using P4 Isolation Forest.
        Args: [air, process, rpm, torque, wear] (5 features)
        Returns: (is_anomaly: bool, anomaly_score: float)
        """
        if _ml_model_p4 is None:
            return False, 0.0
        try:
            pred = _ml_model_p4.predict([features])[0]
            score = _ml_model_p4.decision_function([features])[0]
            return bool(pred == -1), float(score)
        except Exception:
            return False, 0.0

    # ==================== P5: Work Order Priority ====================
    @staticmethod
    def predict_priority(features: List[float]) -> str:
        """
        Predict work order priority level using P5 model.
        Args: [air, process, rpm, torque, wear, temp_delta]
        Returns: priority level
        """
        if _ml_model_p5 is None:
            return "Medium"

        try:
            pred_idx = _ml_model_p5.predict([features])[0]
            return _p5_labels[pred_idx]
        except Exception:
            return "Medium"

    # ==================== P6: Maintenance Schedule ====================
    @staticmethod
    def predict_maintenance_schedule(features: List[float]) -> float:
        """
        Predict optimal days to schedule maintenance using P6.
        Args: [air, process, rpm, torque, wear, temp_delta]
        Returns: days
        """
        if _ml_model_p6 is None:
            return 7.0

        try:
            days = _ml_model_p6.predict([features])[0]
            return max(0.0, float(days))
        except Exception:
            return 7.0

    # ==================== Unified Prediction ====================
    @staticmethod
    def predict_all(telemetry: Dict) -> Dict:
        """
        Get all P1-P6 predictions from a single telemetry input.
        
        Expected telemetry:
        {
            "air_temperature": float,
            "process_temperature": float,
            "rotational_speed": int,
            "torque": float,
            "tool_wear": int
        }
        """
        # Extract features
        air = float(telemetry.get("air_temperature", 298))
        process = float(telemetry.get("process_temperature", 308))
        rpm = int(telemetry.get("rotational_speed", 1500))
        torque = float(telemetry.get("torque", 40))
        wear = int(telemetry.get("tool_wear", 0))
        
        # 5-feature vector
        features_5 = [air, process, rpm, torque, wear]
        
        # 6-feature vector (with temp_delta)
        temp_delta = process - air
        features_6 = features_5 + [temp_delta]
        
        # 7-feature vector (with rpm_torque for P1)
        rpm_torque = (rpm * torque) / 1000.0
        features_7 = features_6 + [rpm_torque]

        # Run all predictions
        failure_prob = MachineLearningService.predict_failure_probability(features_7)
        failure_types = MachineLearningService.predict_failure_type(features_6)
        rul_days = MachineLearningService.predict_rul(features_5)
        is_anomaly, anomaly_score = MachineLearningService.detect_anomaly(features_5)
        priority = MachineLearningService.predict_priority(features_6)
        schedule_days = MachineLearningService.predict_maintenance_schedule(features_6)

        # Determine risk level
        if failure_prob >= 75:
            risk_level = "CRITICAL"
        elif failure_prob >= 50:
            risk_level = "HIGH"
        elif failure_prob >= 25:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "p1_failure_probability": failure_prob,
            "p1_risk_level": risk_level,
            "p2_failure_types": failure_types,
            "p3_rul_days": round(rul_days, 1) if rul_days else None,
            "p4_is_anomaly": is_anomaly,
            "p4_anomaly_score": round(anomaly_score, 3),
            "p5_predicted_priority": priority,
            "p6_schedule_days": round(schedule_days, 1),
        }