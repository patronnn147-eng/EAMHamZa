import json
import numpy as np
import pandas as pd
import joblib
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from sklearn.linear_model import LinearRegression
from models.ordres_intervention import Ordres_intervention
from models.machines import Machines
from models.ml_prediction_log import MlPredictionLog
from .services.ml_xai import XAIService


# Load the trained ML models
MODELS_DIR = os.path.join(os.path.dirname(__file__), 'models')

# P1: Binary Failure Model
P1_MODEL_PATH = os.path.join(MODELS_DIR, 'basic_machine_model.pkl')
try:
    _ml_model_p1 = joblib.load(P1_MODEL_PATH)
    print(f"[OK] P1 model loaded from {P1_MODEL_PATH}")
except Exception as e:
    print(f"[WARN] Failed to load P1 model: {e}")
    _ml_model_p1 = None

# P2: Failure Type Model
P2_MODEL_PATH = os.path.join(MODELS_DIR, 'ml_model_p2_failure_type.pkl')
try:
    _ml_model_p2_data = joblib.load(P2_MODEL_PATH)
    _ml_model_p2 = _ml_model_p2_data['model']
    _p2_features = _ml_model_p2_data.get('features')
    _p2_labels   = _ml_model_p2_data.get('labels')
    print(f"[OK] P2 model loaded from {P2_MODEL_PATH}")
except Exception as e:
    print(f"[WARN] Failed to load P2 model: {e}")
    _ml_model_p2 = None
    _p2_features = None
    _p2_labels   = None

# P3: RUL Estimation Model
P3_MODEL_PATH = os.path.join(MODELS_DIR, 'ml_model_p3_rul.pkl')
try:
    _ml_model_p3 = joblib.load(P3_MODEL_PATH)
    print(f"[OK] P3 model loaded from {P3_MODEL_PATH}")
except Exception as e:
    print(f"[WARN] Failed to load P3 model: {e}")
    _ml_model_p3 = None

# P5: Work Order Priority Model
P5_MODEL_PATH = os.path.join(MODELS_DIR, 'ml_model_p5_priority.pkl')
try:
    _ml_model_p5_data = joblib.load(P5_MODEL_PATH)
    _ml_model_p5 = _ml_model_p5_data['model']
    _p5_labels   = _ml_model_p5_data['labels']
    print(f"[OK] P5 model loaded from {P5_MODEL_PATH}")
except Exception as e:
    print(f"[WARN] Failed to load P5 model: {e}")
    _ml_model_p5 = None
    _p5_labels   = None

# P4: Anomaly Detection Model
P4_MODEL_PATH = os.path.join(MODELS_DIR, 'ml_model_p4_anomaly.pkl')
try:
    _ml_model_p4 = joblib.load(P4_MODEL_PATH)
    print(f"[OK] P4 model loaded from {P4_MODEL_PATH}")
except Exception as e:
    print(f"[WARN] Failed to load P4 model: {e}")
    _ml_model_p4 = None

# P6: Maintenance Schedule Optimization Model
P6_MODEL_PATH = os.path.join(MODELS_DIR, 'ml_model_p6_schedule.pkl')
try:
    _ml_model_p6 = joblib.load(P6_MODEL_PATH)
    print(f"[OK] P6 model loaded from {P6_MODEL_PATH}")
except Exception as e:
    print(f"[WARN] Failed to load P6 model: {e}")
    _ml_model_p6 = None


class MachineLearningService:

    @staticmethod
    def calculate_rul(machine: Machines, interventions: List[Ordres_intervention]) -> Dict:
        """
        Calculate Remaining Useful Life (RUL) for a machine.

        Strategy:
          - MTBF: average days between past interventions
          - LinearRegression decay: projects when health score hits zero
          - ML model probability: if we have a recent telemetry snapshot stored
            on the machine record, use it to blend a model-based failure probability.

        Returns a dictionary with:
          machine_id, machine_name, rul_days, risk_level,
          failure_probability, predicted_failure_date, data_points
        """
        now = datetime.now(timezone.utc)

        # --- Step 1: MTBF-based RUL ---
        mtbf_days = MachineLearningService._get_historical_mtbf(interventions)

        # --- Step 2: Advanced RUL Prediction (ML Model or Linear Decay) ---
        # We prefer the pre-trained XGBoost model if available
        model_rul = MachineLearningService._predict_model_rul(machine)
        
        if model_rul is not None:
            # Model-based RUL (cycles/days)
            # Blend with history for stability: 60% ML, 40% MTBF
            rul_days = (model_rul * 0.6) + (mtbf_days * 0.4)
        else:
            # Fallback to simple MTBF if no model/data
            rul_days = mtbf_days

        # --- Step 3: ML model probability (blended in if model is loaded) ---
        ml_probability: Optional[float] = None
        if _ml_model_p1 is not None:
            # Use machine telemetry if available on the model object,
            # otherwise fall back to reasonable defaults from the dataset mean.
            air_temp     = getattr(machine, 'air_temperature',     300.0) or 300.0
            process_temp = getattr(machine, 'process_temperature', 310.0) or 310.0
            rpm          = getattr(machine, 'rotational_speed',    1500)  or 1500
            torque       = getattr(machine, 'torque',              40.0)  or 40.0
            tool_wear    = getattr(machine, 'tool_wear',           0)     or 0

            features = [float(air_temp), float(process_temp),
                        float(rpm), float(torque), float(tool_wear)]
            ml_probability = MachineLearningService.predict_failure_probability(features)

            # --- Step 3.5: Explain with SHAP (XAI) ---
            feature_names = ["Air temperature [K]", "Process temperature [K]", 
                             "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]"]
            raw_explanations = XAIService.explain_prediction(_ml_model_p1, features, feature_names)
            
            # Map to friendly names
            explanations = [
                {
                    "factor": XAIService.get_friendly_factor_name(exp["factor"]),
                    "impact": exp["impact"],
                    "intensity": exp["intensity"]
                }
                for exp in raw_explanations
            ]
        else:
            explanations = []

        # --- Step 4: Blend RUL-derived probability with ML model probability ---
        rul_probability = round((1 / (1 + np.exp((rul_days - 15) / 5))) * 100, 1)

        if ml_probability is not None:
            # Weight: 60% ML model, 40% RUL-derived sigmoid
            failure_probability = round((0.6 * ml_probability) + (0.4 * rul_probability), 1)
        else:
            failure_probability = rul_probability

        # --- Step 5: Risk level from blended probability ---
        if failure_probability >= 70 or rul_days < 7:
            risk_level = "CRITICAL"
        elif failure_probability >= 50 or rul_days < 15:
            risk_level = "HIGH"
        elif failure_probability >= 30 or rul_days < 30:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # --- Step 6: ML Priority Prediction (P5) ---
        predicted_priority = risk_level.title() # Default to capitalized risk level string
        if _ml_model_p5 is not None:
             p5_features = [float(air_temp), float(process_temp),
                            float(rpm), float(torque), float(tool_wear)]
             predicted_priority = MachineLearningService.predict_priority(p5_features)

        # --- Step 7: Anomaly Detection (P4) ---
        is_anomaly = False
        anomaly_score = 0.0
        if _ml_model_p4 is not None:
            p4_features = [float(air_temp), float(process_temp),
                           float(rpm), float(torque), float(tool_wear)]
            is_anomaly, anomaly_score = MachineLearningService.detect_anomaly(p4_features)

        return {
            "machine_id": machine.id,
            "machine_name": machine.nom,
            "rul_days": round(max(0, rul_days), 1),
            "risk_level": risk_level,
            "failure_probability": failure_probability,
            "predicted_failure_date": (now + timedelta(days=max(0, rul_days))).isoformat(),
            "data_points": len(interventions),
            "ml_model_used": _ml_model_p1 is not None,
            "predicted_priority": predicted_priority,
            "is_anomaly": is_anomaly,
            "anomaly_score": round(float(anomaly_score), 4),
            "explanations": explanations,
            "air_temperature": air_temp,
            "process_temperature": process_temp,
            "rotational_speed": rpm,
            "torque": torque,
            "tool_wear": tool_wear
        }

    @staticmethod
    def predict_failure_probability(features: List[float]) -> float:
        """
        Predict failure probability using the trained .pkl ML model.

        Args:
            features: [air_temp, process_temp, rpm, torque, tool_wear]
                      — must match the exact column order used during training.

        Returns:
            Probability of failure as a float between 0 and 100.
        """
        if _ml_model_p1 is None:
            return 0.0
        prob = _ml_model_p1.predict_proba([features])[0, 1]
        return round(prob * 100, 1)

    @staticmethod
    def predict_failure_type(features: List[float]) -> Dict:
        """
        Predict specific failure types using the trained P2 model.
        Features must match order used in training: 
        [air, process, rpm, torque, wear, temp_delta]
        """
        if _ml_model_p2 is None:
            return {}
        
        # Ensure input is a dataframe if needed, or just a list of lists
        # The training script used features list + temp_delta
        input_data = [features]
        # MultiOutputClassifier.predict returns a 2D array [sample_idx][label_idx]
        predictions = _ml_model_p2.predict(input_data)[0]
        
        # Get probabilities for each label
        # estimators_ is a list of classifiers, one for each label
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
        Features: [air, process, rpm, torque, wear]
        """
        if _ml_model_p5 is None:
            return "Medium"
        
        try:
            pred_idx = _ml_model_p5.predict([features])[0]
            return _p5_labels[pred_idx]
        except Exception:
            return "Medium"

    @staticmethod
    def detect_anomaly(features: List[float]) -> (bool, float):
        """
        Detect machine anomaly using the P4 Isolation Forest model.
        Features: [air, process, rpm, torque, wear]
        Returns: (is_anomaly: bool, anomaly_score: float)
        """
        if_model = _ml_model_p4
        if if_model is None:
            return False, 0.0
        
        try:
            # predict() returns 1 for normal, -1 for anomaly
            pred = if_model.predict([features])[0]
            # decision_function() returns a score (negative = anomaly)
            score = if_model.decision_function([features])[0]
            return bool(pred == -1), float(score)
        except Exception:
            return False, 0.0

    @staticmethod
    def predict_maintenance_schedule(features: List[float]) -> float:
        """
        Predict the optimal number of days to schedule maintenance.
        Features: [air, process, rpm, torque, wear]
        Returns: recommended days until maintenance (float)
        """
        if _ml_model_p6 is None:
            return 7.0  # Default fallback
        
        try:
            days = _ml_model_p6.predict([features])[0]
            return max(0.0, float(days))  # Ensure non-negative
        except Exception:
            return 7.0

    @staticmethod
    def _get_historical_mtbf(
        interventions: List[Ordres_intervention],
        default_days: float = 60.0
    ) -> float:
        """Calculate Mean Time Between Failures (MTBF) from intervention history."""
        if len(interventions) < 2:
            return default_days
        raw_dates = [i.date_intervention for i in interventions if i.date_intervention]
        if len(raw_dates) < 2:
            return default_days
        dates = sorted(raw_dates)
        gaps = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
        return float(np.mean(gaps)) if gaps else default_days

    @staticmethod
    def _predict_model_rul(machine: Machines) -> Optional[float]:
        """
        Use the pre-trained P3 XGBoost Regressor to estimate RUL
        based on current telemetry.
        """
        if _ml_model_p3 is None:
            return None

        # Extract features (must match sanitized names logic if needed, 
        # but here we just pass the values in order)
        air_temp     = getattr(machine, 'air_temperature',     300.0) or 300.0
        process_temp = getattr(machine, 'process_temperature', 310.0) or 310.0
        rpm          = getattr(machine, 'rotational_speed',    1500)  or 1500
        torque       = getattr(machine, 'torque',              40.0)  or 40.0
        tool_wear    = getattr(machine, 'tool_wear',           0)     or 0

        # Feature order must match training: [air, process, rpm, torque, wear]
        input_data = np.array([[
            float(air_temp), float(process_temp), float(rpm), 
            float(torque), float(tool_wear)
        ]])

        try:
            # Note: XGBoost might warn about feature names if they were sanitized during training
            # but it will still predict correctly based on position.
            pred_rul = _ml_model_p3.predict(input_data)[0]
            return float(pred_rul)
        except Exception:
            return None

    @staticmethod
    def _project_health_end(
        machine: Machines,
        interventions: List[Ordres_intervention]
    ) -> Optional[float]:
        """
        Legacy method kept for compatibility if needed, but replaced by _predict_model_rul.
        """
        return MachineLearningService._predict_model_rul(machine)

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
