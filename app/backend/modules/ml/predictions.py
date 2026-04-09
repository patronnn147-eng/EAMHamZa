import numpy as np
from typing import List, Dict, Optional

from models.ordres_intervention import Ordres_intervention
from models.machines import Machines
from .model_loader import get_model, _ml_model_p2, _ml_model_p3, _ml_model_p4, _ml_model_p5, _p2_labels, _p5_labels


class MachineLearningService:

    @staticmethod
    def predict_failure_probability(features: List[float]) -> float:
        """
        Predict failure probability using P1 model.
        Args: [air_temp, process_temp, rpm, torque, tool_wear]  (5 features)
        """
        model_p1 = get_model()
        if model_p1 is None:
            return 0.0
        try:
            prob = model_p1.predict_proba([features])[0, 1]
            return round(prob * 100, 1)
        except Exception:
            return 0.0


    @staticmethod
    def predict_failure_type(features: List[float]) -> Dict:
        """
        Predict specific failure types using the trained P2 model.
        Features must match order used in training: 
        [air, process, rpm, torque, wear, temp_delta]
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

    @staticmethod
    def predict_priority(features: List[float]) -> str:
        """
        Predict work order priority level using the P5 model.
        Args: [air, process, rpm, torque, wear, temp_delta]
        """
        if _ml_model_p5 is None:
            return "Medium"
        
        try:
            pred_idx = _ml_model_p5.predict([features])[0]
            return _p5_labels[pred_idx]
        except Exception:
            return "Medium"


    @staticmethod
    def detect_anomaly(features: List[float]) -> tuple:
        """
        Detect machine anomaly using P4 Isolation Forest.
        Args: [air, process, rpm, torque, wear]  (5 features)
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

    @staticmethod
    def predict_maintenance_schedule(features: List[float]) -> float:
        """
        Predict the optimal number of days to schedule maintenance.
        Args: [air, process, rpm, torque, wear, temp_delta]
        """
        from .model_loader import _ml_model_p6
        
        if _ml_model_p6 is None:
            return 7.0

        try:
            days = _ml_model_p6.predict([features])[0]
            return max(0.0, float(days))
        except Exception:
            return 7.0

    @staticmethod
    def _get_historical_mtbf(
        interventions: List[Ordres_intervention],
        default_days: Optional[float] = None
    ) -> float:
        """Calculate Mean Time Between Failures (MTBF) from intervention history."""
        fallback_default = default_days if default_days is not None else 60.0
        
        if len(interventions) < 2:
            return fallback_default
        raw_dates = [i.date_intervention for i in interventions if i.date_intervention]
        if len(raw_dates) < 2:
            return fallback_default
        dates = sorted(raw_dates)
        gaps = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
        return float(np.mean(gaps)) if gaps else fallback_default

    @staticmethod
    def _predict_model_rul(features: List[float]) -> Optional[float]:
        """
        Use the P3 XGBoost Regressor to estimate RUL.
        Args: [air, process, rpm, torque, wear]  (5 features)
        """
        if _ml_model_p3 is None:
            return None
        try:
            pred_rul = _ml_model_p3.predict(np.array([features]))[0]
            return float(pred_rul)
        except Exception:
            return None


    @staticmethod
    def _project_health_end(
        machine: Machines,
        interventions: List[Ordres_intervention]
    ) -> Optional[float]:
        """Legacy method kept for compatibility."""
        air_temp     = getattr(machine, 'air_temperature',     300.0) or 300.0
        process_temp = getattr(machine, 'process_temperature', 310.0) or 310.0
        rpm          = getattr(machine, 'rotational_speed',    1500)  or 1500
        torque       = getattr(machine, 'torque',              40.0)  or 40.0
        tool_wear    = getattr(machine, 'tool_wear',           0)     or 0
        features_5   = [float(air_temp), float(process_temp), float(rpm), float(torque), float(tool_wear)]
        return MachineLearningService._predict_model_rul(features_5)
