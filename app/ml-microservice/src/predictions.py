"""
ML Predictions Service
Provides P1-P6 prediction methods + DST unified health fusion (Wave 2).
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
from .feature_store import FeatureStore
from .health_index import MahalanobisHealthIndex, get_health_index_model
from .survival_model import SurvivalModel, get_survival_model
from .anomaly_cusum import AnomalyEnsemble, get_anomaly_ensemble
from .kalman_estimator import KalmanStateEstimator, get_kalman_estimator
from .dst_fusion import DSTFusion, get_dst_fusion

# Try to import PINN — optional (requires torch)
try:
    from .pinn_rul import PINNRULEstimator, get_pinn_estimator
    _PINN_AVAILABLE = True
except ImportError:
    _PINN_AVAILABLE = False
    get_pinn_estimator = None  # type: ignore


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
        Features: [air, process, rpm, torque, wear, temp_delta] or 7-feature vector.
        Returns: {TWF: {detected, probability}, HDF: {...}, etc.}
        """
        if _ml_model_p2 is None:
            return {}

        try:
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
        except ValueError:
            # Feature shape mismatch — try with 7-feature vector (rpm_torque added)
            try:
                if len(features) == 6:
                    air, process, rpm, torque, wear, temp_delta = features
                    rpm_torque = (float(rpm) * float(torque)) / 1000.0
                    features_7 = [air, process, rpm, torque, wear, temp_delta, rpm_torque]
                    input_data = [features_7]
                    predictions = _ml_model_p2.predict(input_data)[0]
                    probabilities = [est.predict_proba(input_data)[0, 1] for est in _ml_model_p2.estimators_]
                    result = {}
                    for i, label in enumerate(_p2_labels):
                        result[label] = {
                            "detected": bool(predictions[i]),
                            "probability": round(float(probabilities[i]) * 100, 1)
                        }
                    return result
            except Exception:
                pass
            return {}
        except Exception:
            return {}

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

        base_result = {
            "p1_failure_probability": failure_prob,
            "p1_risk_level": risk_level,
            "p2_failure_types": failure_types,
            "p3_rul_days": round(rul_days, 1) if rul_days else None,
            "p4_is_anomaly": is_anomaly,
            "p4_anomaly_score": round(anomaly_score, 3),
            "p5_predicted_priority": priority,
            "p6_schedule_days": round(schedule_days, 1),
        }

        # ==================== Wave 2: DST Fusion Pipeline ====================
        try:
            machine_id = int(telemetry.get("machine_id", -1))
            logs       = telemetry.get("_logs", [])  # injected by caller when available

            # Snapshot for context-aware models
            snapshot = FeatureStore.extract_full_snapshot(
                telemetry,
                context={
                    "machine_id":           machine_id,
                    "days_since_maint":     int(telemetry.get("days_since_maint", -1)),
                    "open_work_orders":     int(telemetry.get("open_work_orders", 0)),
                    "recent_interventions": int(telemetry.get("recent_interventions", 0)),
                    "machine_status":       str(telemetry.get("machine_status", "OPERATIONNELLE")),
                }
            )

            # Time series from logs (for PINN)
            time_series = FeatureStore.build_time_series_from_logs(machine_id, logs) if logs else []

            # --- Model C: Mahalanobis Health Index ---
            model_c_out: Optional[Dict] = None
            hi_model = get_health_index_model()
            if hi_model is not None and hi_model._fitted:
                model_c_out = hi_model.score(np.array(features_5))

            # --- Model E: Anomaly Ensemble ---
            model_e_out: Optional[Dict] = None
            anomaly_model = get_anomaly_ensemble()
            feature_names = ["air_temperature", "process_temperature",
                             "rotational_speed", "torque", "tool_wear"]
            if anomaly_model is not None and anomaly_model._fitted:
                model_e_out = anomaly_model.predict(np.array(features_5), feature_names)

            # --- Model B: Survival Analysis ---
            model_b_out: Optional[Dict] = None
            surv_model = get_survival_model()
            if surv_model is not None and surv_model._fitted:
                model_b_out = surv_model.predict(snapshot)

            # --- Model A: PINN RUL ---
            model_a_out: Optional[Dict] = None
            if _PINN_AVAILABLE and len(time_series) >= 3:
                pinn = get_pinn_estimator()
                if pinn is not None and pinn._fitted:
                    model_a_out = pinn.predict(time_series)

            # --- Kalman state update ---
            # Default health scores when advanced models aren't fitted
            DEFAULT_HI = 75.0  # Assume healthy baseline
            rule_score = max(0.0, 100.0 - failure_prob)  # invert P1 as rule signal
            kalman_obs = {
                "rule_score":   rule_score,
                "ml_score":     rule_score,
                "survival_hi":  model_b_out["health_index"] if model_b_out and not np.isnan(model_b_out.get("health_index", np.nan)) else DEFAULT_HI,
                "mahal_hi":    model_c_out["health_index"] if model_c_out and not np.isnan(model_c_out.get("health_index", np.nan)) else DEFAULT_HI,
            }
            kalman_state = get_kalman_estimator().update(kalman_obs)

            # --- DST Fusion ---
            # Filter out None and NaN model outputs
            valid_outputs = []
            for out in [model_a_out, model_b_out, model_c_out, model_e_out]:
                if out is not None:
                    # Check for valid health_index (not NaN)
                    hi = out.get("health_index")
                    if hi is not None and not np.isnan(hi):
                        valid_outputs.append(out)
            model_outputs = valid_outputs
            fusion_result = get_dst_fusion().fuse(model_outputs, kalman_state)

            base_result.update({
                "unified_health_score":      fusion_result["unified_health_score"],
                "dst_verdict":               fusion_result["dst_verdict"],
                "conflict_factor_K":         fusion_result["conflict_factor_K"],
                "dst_score":                 fusion_result["dst_score"],
                "kalman_hi":                 fusion_result["kalman_hi"],
                "kalman_rul":                fusion_result["kalman_rul"],
                "sensor_fault_flag":         fusion_result["sensor_fault_flag"],
                "model_disagreement_alert":  fusion_result["model_disagreement_alert"],
                "bpa": {
                    "healthy":   fusion_result["bpa_healthy"],
                    "degrading": fusion_result["bpa_degrading"],
                    "critical":  fusion_result["bpa_critical"],
                    "unknown":   fusion_result["bpa_unknown"],
                },
                "model_outputs": {
                    "pinn_rul":  model_a_out,
                    "survival":  model_b_out,
                    "mahal_hi":  model_c_out,
                    "anomaly":   model_e_out,
                },
            })
        except Exception as _fusion_exc:
            import logging as _log
            _log.getLogger(__name__).warning(f"DST fusion failed: {_fusion_exc}", exc_info=True)
            # Graceful fallback: unified_health_score mirrors P1 inversion
            base_result["unified_health_score"] = max(0.0, round(100.0 - failure_prob, 1))
            base_result["dst_verdict"] = risk_level.title()
            base_result["conflict_factor_K"] = 0.0
            base_result["score_source"] = "fallback_additive"

        return base_result