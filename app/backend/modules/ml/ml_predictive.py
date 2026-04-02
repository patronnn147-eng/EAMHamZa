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

_MODEL = None
_MODEL_PATH = os.path.join(MODELS_DIR, 'basic_machine_model.pkl')

def get_model():
    global _MODEL
    if _MODEL is None:
        if os.path.exists(_MODEL_PATH):
            _MODEL = joblib.load(_MODEL_PATH)
    return _MODEL

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
    def calculate_rul(
        machine: Machines, 
        interventions: List[Ordres_intervention],
        open_work_orders: int = 0,
        recent_interventions: int = 0
    ) -> Dict:
        """
        Calculate Remaining Useful Life (RUL) and ML-informed KPIs.
        
        Strategy:
          - RUL (P3): predictive remaining life.
          - Health Score: ML-derived condition index.
          - Reliability: predictive stability index.
        """
        now = datetime.now(timezone.utc)

        # --- Step 1: Telemetry Data Extraction ---
        air_temp     = getattr(machine, 'air_temperature',     300.0) or 300.0
        process_temp = getattr(machine, 'process_temperature', 310.0) or 310.0
        rpm          = getattr(machine, 'rotational_speed',    1500)  or 1500
        torque       = getattr(machine, 'torque',              40.0)  or 40.0
        tool_wear    = getattr(machine, 'tool_wear',           0)     or 0
        temp_delta   = float(process_temp) - float(air_temp)

        # Feature vectors: P1/P3/P4/P6 expect 5 features; P2 expects 6 (with temp_delta)
        features_5 = [float(air_temp), float(process_temp), float(rpm), float(torque), float(tool_wear)]
        features_6 = [float(air_temp), float(process_temp), float(rpm), float(torque), float(tool_wear), temp_delta]

        # --- Step 2: RUL Prediction (P3 - 5 features) ---
        hist_mtbf_days = MachineLearningService._get_historical_mtbf(interventions)
        model_rul = MachineLearningService._predict_model_rul(features_5)

        if model_rul is not None:
            rul_days = (model_rul * 0.7) + (hist_mtbf_days * 0.3)
        else:
            rul_days = hist_mtbf_days

        # --- Step 3: Failure Probability (P1 - 5 features) ---
        ml_probability: float = 0.0
        model_p1 = get_model()
        if model_p1 is not None:
            ml_probability = MachineLearningService.predict_failure_probability(features_5)

        # --- Step 4: Anomaly Detection (P4 - 5 features) ---
        is_anomaly = False
        anomaly_score = 0.0
        if _ml_model_p4 is not None:
            is_anomaly, anomaly_score = MachineLearningService.detect_anomaly(features_5)

        # --- Step 5: Operational Deductions (Maintenance, Status, Tickets) ---
        now_dt = datetime.now(timezone.utc)
        
        # 5a. Maintenance Age
        maint_date = machine.date_derniere_maintenance
        if maint_date:
            # Ensure maint_date is offset-aware for comparison
            if maint_date.tzinfo is None:
                maint_date = maint_date.replace(tzinfo=timezone.utc)
            days_since_maint = (now_dt - maint_date).days
        else:
            days_since_maint = -1 # Never maintained
            
        maint_deduction = max(0, min(days_since_maint * 0.5, 30)) if days_since_maint > 0 else 0
        
        # 5b. Overdue Maintenance
        overdue_deduction = 0
        next_maint = machine.date_prochaine_maintenance
        if next_maint:
            if next_maint.tzinfo is None:
                next_maint = next_maint.replace(tzinfo=timezone.utc)
            if now_dt > next_maint:
                days_overdue = (now_dt - next_maint).days
                overdue_deduction = min(days_overdue * 2, 40)
        
        # 5c. Machine Status (Down/Stopped)
        status_deduction = 60 if machine.statut in ["EN_PANNE", "HORS_SERVICE"] else 0
        
        # 5d. Work Orders & Recent Interventions
        wo_deduction = min(open_work_orders * 12, 36)
        ri_deduction = min(recent_interventions * 10, 30)

        # --- Step 6: ML-Informed Health Score (0-100) ---
        # Starts from predictive health, then applies operational penalties
        predictive_health = 100 - ml_probability
        anomaly_penalty = 0.0
        if is_anomaly:
            anomaly_penalty = min(40, abs(anomaly_score) * 150)
            predictive_health -= anomaly_penalty
        
        ml_health_score = predictive_health - (maint_deduction + overdue_deduction + status_deduction + wo_deduction + ri_deduction)
        ml_health_score = max(0, min(100, ml_health_score))

        # --- Step 7: ML-Informed Reliability Score (0-100) ---
        reliability_base = min(100, (rul_days / 60) * 100) if rul_days < 60 else 100
        ml_reliability_score = max(0, min(100, reliability_base * (1 - (ml_probability / 200))))

        # --- Step 7: Predicted KPIs (MTBF, MTTR, Availability) ---
        if len(interventions) == 0:
            ml_mtbf_hours = None
            ml_mttr_hours = None
            ml_availability_pct = None
            ml_health_score = 100.0  # Perfect health for new machine
            ml_reliability_score = None # No reliability score yet
            risk_level = "LOW" # Basic assumption
            predicted_priority = "Normal"
        else:
            ml_mtbf_hours = rul_days * 24
            ml_mttr_hours = 2.5
            if _ml_model_p2 is not None:
                # P2 uses 6 features (includes temp_delta)
                types = MachineLearningService.predict_failure_type(features_6)
                for t_name, t_data in types.items():
                    if t_data["detected"]:
                        if t_name in ["HDF", "OSF"]: ml_mttr_hours += 1.5
                        if t_name == "TWF": ml_mttr_hours += 0.5
            ml_availability_pct = max(0, min(100.0, 100.0 - (ml_probability * 0.1)))

        # --- Step 8: Risk Level & Priority (P5 - 5 features) ---
        if ml_probability >= 70 or rul_days < 7: risk_level = "CRITICAL"
        elif ml_probability >= 50 or rul_days < 15: risk_level = "HIGH"
        elif ml_probability >= 30 or rul_days < 30: risk_level = "MEDIUM"
        else: risk_level = "LOW"

        predicted_priority = MachineLearningService.predict_priority(features_5) if _ml_model_p5 else risk_level.title()

        # SHAP Explanations (P1 - 5 features)
        explanations = []
        if model_p1 is not None:
            feature_names = ["Air temperature [K]", "Process temperature [K]", "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]"]
            raw_explanations = XAIService.explain_prediction(model_p1, features_5, feature_names)
            explanations = [{"factor": XAIService.get_friendly_factor_name(e["factor"]), "impact": e["impact"], "intensity": e["intensity"]} for e in raw_explanations]

        response = {
            "machine_id": machine.id,
            "machine_name": machine.nom,
            "rul_days": round(max(0, rul_days), 1),
            "risk_level": risk_level,
            "failure_probability": ml_probability,
            "predicted_failure_date": (now + timedelta(days=max(0, rul_days))).isoformat(),
            "data_points": len(interventions),
            "ml_model_used": model_p1 is not None,
            "predicted_priority": predicted_priority,
            "is_anomaly": is_anomaly,
            "anomaly_score": round(float(anomaly_score), 4),
            "explanations": explanations,
            
            # New Unified ML-Informed Health
            "health_score": round(ml_health_score, 1) if ml_health_score is not None else None,
            "health_breakdown": {
                "predictive_risk": round(ml_probability, 1),
                "anomaly_penalty": round(min(40, abs(anomaly_score) * 150), 1) if is_anomaly else 0,
                "maintenance_deduction": round(maint_deduction, 1),
                "overdue_deduction": round(overdue_deduction, 1),
                "status_deduction": round(status_deduction, 1),
                "work_order_deduction": round(wo_deduction, 1),
                "intervention_deduction": round(ri_deduction, 1),
                "days_since_maintenance": days_since_maint,
                "open_work_orders": open_work_orders,
                "recent_interventions": recent_interventions
            },
            "reliability_score": round(ml_reliability_score, 1) if ml_reliability_score is not None else None,
            "mtbf_pred": round(ml_mtbf_hours, 1) if ml_mtbf_hours is not None else None,
            "mttr_pred": round(ml_mttr_hours, 1) if ml_mttr_hours is not None else None,
            "availability_pred": round(ml_availability_pct, 1) if ml_availability_pct is not None else None,
            
            # Raw Telemetry (for reference)
            "air_temperature": air_temp,
            "process_temperature": process_temp,
            "rotational_speed": rpm,
            "torque": torque,
            "tool_wear": tool_wear
        }

        if model_p1 is None:
            response["model_unavailable"] = True

        return response


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
        default_days: Optional[float] = None
    ) -> float:
        """Calculate Mean Time Between Failures (MTBF) from intervention history."""
        # Use a safe fallback if no default is provided, but the goal is to return the default
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
