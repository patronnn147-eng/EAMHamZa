"""
ML Predictions Service
Provides P1-P6 prediction methods + DST unified health fusion (Wave 2).
"""
import logging
import numpy as np
from typing import List, Dict, Optional

from .model_loader import (
    get_model,
    _ml_model_p2,
    _ml_model_p3,
    _ml_model_p4,
    _p4_weights,
    _p4_thresholds,
    _p4_training_stats,
    _p4_ae_scaler,
    _p4_autoencoder,
    _p4_feature_pipeline,
    _p4_ensemble_type,
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

logger = logging.getLogger(__name__)

# Try to import PINN -- optional (requires torch)
try:
    from .pinn_rul import PINNRULEstimator, get_pinn_estimator
    _PINN_AVAILABLE = True
except ImportError:
    _PINN_AVAILABLE = False
    get_pinn_estimator = None  # type: ignore

# Try to import MOMENT -- optional (requires momentfm + torch)
try:
    from .moment_estimator import (
        get_moment_anomaly_detector,
        get_moment_rul_estimator,
        MOMENT_AVAILABLE as _MOMENT_AVAILABLE,
    )
except ImportError:
    _MOMENT_AVAILABLE = False
    get_moment_anomaly_detector = None  # type: ignore
    get_moment_rul_estimator    = None  # type: ignore



def failure_prob_to_risk(prob: float) -> str:
    """Map failure probability (0-100) to risk level string.

    Thresholds:  >= 75 -> CRITICAL, >= 50 -> HIGH, >= 25 -> MEDIUM, else LOW.
    Single authoritative definition -- import this instead of duplicating.
    """
    if prob >= 75:
        return "CRITICAL"
    if prob >= 50:
        return "HIGH"
    if prob >= 25:
        return "MEDIUM"
    return "LOW"

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
            logger.warning("P1 failure probability prediction failed", exc_info=True)
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
            # Feature shape mismatch -- try with 7-feature vector (rpm_torque added)
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
                logger.warning("P2 failure type prediction failed (fallback)", exc_info=True)
            return {}
        except Exception:
            logger.warning("P2 failure type prediction failed", exc_info=True)
            return {}

    # ==================== P3: RUL Estimation ====================
    @staticmethod
    def predict_rul(features: List[float]) -> Optional[float]:
        """
        Predict Remaining Useful Life using P3 XGBoost.
        Args: [air, process, rpm, torque, wear] (5) or
              [air, process, rpm, torque, wear, temp_delta, rpm_torque] (7)
        Returns: days until failure
        """
        if _ml_model_p3 is None:
            return None
        try:
            # P3 trained on 7 features. Auto-derive temp_delta + rpm_torque.
            if len(features) == 5:
                air, process, rpm, torque, wear = features
                temp_delta = float(process) - float(air)
                rpm_torque = (float(rpm) * float(torque)) / 1000.0
                features = [air, process, rpm, torque, wear, temp_delta, rpm_torque]
            pred_rul = _ml_model_p3.predict(np.array([features]))[0]
            return float(pred_rul)
        except Exception:
            logger.warning("P3 RUL prediction failed", exc_info=True)
            return None

    # ==================== P4: Anomaly Detection ====================
    @staticmethod
    def detect_anomaly(features: List[float]) -> tuple:
        """
        Detect machine anomaly using P4 ensemble (IF + Z-Score + Cluster + optional AE).
        Args: [air, process, rpm, torque, wear] (5 raw sensors)
        Returns: (is_anomaly: bool, anomaly_score: float 0-1)
        """
        if _ml_model_p4 is None:
            return False, 0.0

        try:
            # Always work with 5 raw sensor features
            x5 = np.array(features[:5], dtype=float).reshape(1, -1)

            component_scores:  dict = {}
            component_weights: dict = {}

            # -- 1. Isolation Forest (always available) ----------------
            # decision_function: lower = more anomalous; negate so higher = more anomalous
            if_raw = float(-_ml_model_p4.decision_function(x5)[0])
            component_scores['if']  = if_raw
            component_weights['if'] = _p4_weights.get('if', 0.30)

            # -- 2. Autoencoder (optional - needs TensorFlow) ----------
            if _p4_autoencoder is not None and _p4_ae_scaler is not None:
                try:
                    x_scaled = _p4_ae_scaler.transform(x5)
                    x_recon  = _p4_autoencoder.predict(x_scaled, verbose=0)
                    ae_raw   = float(np.mean((x_scaled - x_recon) ** 2))
                    component_scores['ae']  = ae_raw
                    component_weights['ae'] = _p4_weights.get('ae', 0.40)
                except Exception:
                    pass  # TF inference failed - skip silently

            # -- 3. Z-Score (needs training_stats in pkl) --------------
            t_mean = _p4_training_stats.get('mean')
            t_std  = _p4_training_stats.get('std')
            if t_mean and t_std:
                mean_arr = np.array(t_mean)
                std_arr  = np.array(t_std)
                std_arr[std_arr == 0] = 1.0  # avoid div-by-zero
                z_scores = np.abs((x5[0] - mean_arr) / std_arr)
                z_raw    = float(np.max(z_scores))
                component_scores['zscore']  = z_raw
                component_weights['zscore'] = _p4_weights.get('zscore', 0.20)

            # -- 4. Cluster Deviation (needs feature pipeline) ---------
            if _p4_feature_pipeline is not None:
                try:
                    import pandas as pd
                    SENSOR_COLS = [
                        'Air temperature [K]', 'Process temperature [K]',
                        'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]'
                    ]
                    df_snap  = pd.DataFrame(x5, columns=SENSOR_COLS)
                    x_v3     = _p4_feature_pipeline.transform(df_snap)
                    if hasattr(x_v3, 'columns') and 'cluster_distance' in x_v3.columns:
                        cluster_raw = float(x_v3['cluster_distance'].values[0])
                        component_scores['cluster']  = cluster_raw
                        component_weights['cluster'] = _p4_weights.get('cluster', 0.10)
                except Exception:
                    pass  # pipeline inference failed - skip silently

            # -- Normalize each component to [0, 1] using training thresholds
            def _norm(name: str, raw: float) -> float:
                lo = _p4_thresholds.get(f'{name}_min', 0.0)
                hi = _p4_thresholds.get(f'{name}_max', 1.0)
                if hi == lo:
                    return 0.5
                return float(np.clip((raw - lo) / (hi - lo), 0.0, 1.0))

            # -- Weighted ensemble score (renormalized across available components)
            total_weight = sum(component_weights.values())
            if total_weight == 0:
                return False, 0.0

            ensemble_score = sum(
                _norm(name, score) * component_weights[name]
                for name, score in component_scores.items()
            ) / total_weight

            is_anomaly = ensemble_score > 0.5
            return is_anomaly, round(ensemble_score, 4)

        except Exception:
            logger.warning("P4 anomaly detection failed", exc_info=True)
            # Fallback: bare IF prediction
            try:
                x_fb  = np.array(features[:5]).reshape(1, -1)
                pred  = _ml_model_p4.predict(x_fb)[0]
                score = float(-_ml_model_p4.decision_function(x_fb)[0])
                return bool(pred == -1), round(score, 4)
            except Exception:
                return False, 0.0

    # ==================== P5: Work Order Priority ====================
    @staticmethod
    def predict_priority(features: List[float]) -> str:
        """
        Predict work order priority level using P5 model.
        Args: [air, process, rpm, torque, wear, temp_delta] (6 features) OR
              [air, process, rpm, torque, wear, temp_delta, rpm_torque] (7 features)
        Returns: priority level string
        """
        if _ml_model_p5 is None:
            return "Medium"

        try:
            # P5 model trained on 7 features. Auto-derive rpm_torque when
            # caller provides 6 so both call-sites work without shape errors.
            if len(features) == 6:
                rpm_torque = (float(features[2]) * float(features[3])) / 1000.0
                features = list(features) + [rpm_torque]
            pred_idx = _ml_model_p5.predict([features])[0]
            return _p5_labels[pred_idx]
        except Exception:
            logger.warning("P5 priority prediction failed", exc_info=True)
            return "Medium"

    # ==================== P6: Maintenance Schedule ====================
    @staticmethod
    def predict_maintenance_schedule(features: List[float]) -> float:
        """
        Predict optimal days to schedule maintenance using P6.
        Args: [air, process, rpm, torque, wear, temp_delta] (6) or
              [air, process, rpm, torque, wear, temp_delta, rpm_torque] (7) or
              [air, process, rpm, torque, wear, temp_delta, rpm_torque, tool_wear_sq] (8)
        Returns: days
        """
        if _ml_model_p6 is None:
            return 7.0

        try:
            # P6 trained on 8 features. Auto-derive derived features.
            if len(features) >= 5:
                air   = float(features[0])
                rpm   = float(features[2])
                torque = float(features[3])
                wear  = float(features[4])
                temp_delta = float(features[5]) if len(features) > 5 else (float(features[1]) - air)
                rpm_torque = float(features[6]) if len(features) > 6 else (rpm * torque) / 1000.0
                tool_wear_sq = float(features[7]) if len(features) > 7 else wear ** 2
                features = [air, float(features[1]), rpm, torque, wear,
                            temp_delta, rpm_torque, tool_wear_sq]
            days = _ml_model_p6.predict([features])[0]
            return max(0.0, float(days))
        except Exception:
            logger.warning("P6 maintenance schedule prediction failed", exc_info=True)
            return 7.0

    # ==================== Unified Prediction ====================
    @staticmethod
    def predict_all(telemetry: Dict, include_shap: bool = False) -> Dict:
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

        risk_level = failure_prob_to_risk(failure_prob)

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
            logs       = telemetry.get("telemetry_logs", [])  # injected by caller when available

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
            # Global singleton is None until explicitly fitted externally.
            # When it's absent, spin up a fresh local instance so that
            # fit_and_score_history() can train on history[:-1] and score
            # history[-1] on-the-fly.  Requires 11+ logs for a real result
            # (10 training points -> fit succeeds; < 11 returns dm2=0.0).
            if hi_model is None and len(logs) >= 2:
                hi_model = MahalanobisHealthIndex()
            if hi_model is not None:
                if len(logs) >= 2:
                    history_matrix = np.array([
                        [
                            float(lg.get("air_temperature", 298)),
                            float(lg.get("process_temperature", 308)),
                            float(lg.get("rotational_speed", 1500)),
                            float(lg.get("torque", 40)),
                            float(lg.get("tool_wear", 0)),
                        ]
                        for lg in logs
                    ])
                    model_c_out = hi_model.fit_and_score_history(history_matrix)
                elif hi_model._fitted:
                    model_c_out = hi_model.score(np.array(features_5))

            # --- Model E: Anomaly Ensemble (stateless -- safe under concurrent requests) ---
            model_e_out: Optional[Dict] = None
            anomaly_model = get_anomaly_ensemble()
            feature_names = ["air_temperature", "process_temperature",
                             "rotational_speed", "torque", "tool_wear"]
            if anomaly_model is not None and anomaly_model._fitted:
                # Build history arrays (all entries except the latest)
                history_arrays = [
                    np.array([
                        float(lg.get("air_temperature", 298)),
                        float(lg.get("process_temperature", 308)),
                        float(lg.get("rotational_speed", 1500)),
                        float(lg.get("torque", 40)),
                        float(lg.get("tool_wear", 0)),
                    ])
                    for lg in logs[:-1]  # exclude latest -- that's what we score
                ] if len(logs) > 1 else []
                # predict_with_history creates fresh CUSUM detectors per call --
                # no shared mutable state, safe for concurrent requests.
                model_e_out = anomaly_model.predict_with_history(
                    np.array(features_5),
                    feature_names,
                    history=history_arrays,
                )

            # --- Model B: Survival Analysis ---
            # Create a fresh local instance when fitting from logs to avoid
            # mutating the global singleton under concurrent requests.
            # The global singleton is only used read-only as a pre-trained fallback.
            model_b_out: Optional[Dict] = None
            if len(logs) >= 10:
                local_surv = SurvivalModel()
                try:
                    local_surv.fit_from_logs(logs)
                    if local_surv._fitted:
                        model_b_out = local_surv.predict(snapshot)
                except Exception as _e:
                    logger.warning(f"Survival fit_from_logs failed: {_e}")
            else:
                # Not enough logs to fit machine-specific model -- use global pre-trained
                global_surv = get_survival_model()
                if global_surv is not None and global_surv._fitted:
                    model_b_out = global_surv.predict(snapshot)

            # --- Model A: PINN RUL ---
            model_a_out: Optional[Dict] = None
            if _PINN_AVAILABLE and len(time_series) >= 3:
                pinn = get_pinn_estimator()
                if pinn is not None and pinn._fitted:
                    model_a_out = pinn.predict(time_series)

            # --- Model M: MOMENT Foundation Model ---
            model_m_anomaly_out: Optional[Dict] = None
            model_m_rul_out:     Optional[Dict] = None
            if _MOMENT_AVAILABLE and len(logs) >= 3:
                try:
                    detector = get_moment_anomaly_detector()
                    if detector is not None:
                        model_m_anomaly_out = detector.predict(logs)
                except Exception as _me:
                    logger.warning(f"MOMENT anomaly failed: {_me}")
                try:
                    rul_est = get_moment_rul_estimator()
                    if rul_est is not None:
                        model_m_rul_out = rul_est.predict(logs)
                except Exception as _me:
                    logger.warning(f"MOMENT RUL failed: {_me}")

            # --- Kalman state update (fresh instance per request -- no shared state) ---
            # Default health scores when advanced models aren't fitted
            DEFAULT_HI = 75.0  # Assume healthy baseline
            rule_score = max(0.0, 100.0 - failure_prob)  # invert P1 as rule signal

            # A new KalmanStateEstimator is created per request. It is cheap to
            # construct and avoids the race condition where concurrent requests
            # would overwrite the same filter's x/P matrices.
            kalman = KalmanStateEstimator()

            if len(logs) >= 2:
                # Build simplified observation sequence from history.
                # Each entry embeds "dt" (days since previous reading) so Kalman
                # uses real elapsed time rather than a hardcoded 1-day assumption.
                from datetime import datetime as _dt_cls

                def _parse_ts(s: str):
                    """Parse ISO timestamp; return None on failure."""
                    if not s:
                        return None
                    try:
                        return _dt_cls.fromisoformat(s.replace("Z", "+00:00"))
                    except Exception:
                        return None

                kalman_history = []
                prev_ts = None
                for lg in logs[:-1]:
                    air_h  = float(lg.get("air_temperature", 298))
                    hi_est = max(0.0, min(100.0, 100.0 - (air_h - 298) * 2.0))
                    ts     = _parse_ts(lg.get("created_at", ""))
                    if prev_ts is not None and ts is not None:
                        # Clamp to [10 min, 30 days] to handle outlier gaps
                        elapsed_sec = (ts - prev_ts).total_seconds()
                        dt_days = max(10 / 1440.0, min(30.0, elapsed_sec / 86400.0))
                    else:
                        dt_days = 1.0  # default: assume daily cadence
                    kalman_history.append({"rule_score": hi_est, "dt": dt_days})
                    prev_ts = ts

                # Final observation uses all available model scores.
                # dt for the last step: gap between penultimate and last log entry.
                last_ts = _parse_ts(logs[-1].get("created_at", "")) if logs else None
                if prev_ts is not None and last_ts is not None:
                    elapsed_last = (last_ts - prev_ts).total_seconds()
                    final_dt = max(10 / 1440.0, min(30.0, elapsed_last / 86400.0))
                else:
                    final_dt = 1.0
                kalman_history.append({
                    "rule_score":  rule_score,
                    "ml_score":    rule_score,
                    "survival_hi": model_b_out["health_index"] if model_b_out and not np.isnan(model_b_out.get("health_index", np.nan)) else DEFAULT_HI,
                    "mahal_hi":    model_c_out["health_index"] if model_c_out and not np.isnan(model_c_out.get("health_index", np.nan)) else DEFAULT_HI,
                    "dt":          final_dt,
                })
                kalman_state = kalman.smooth_from_scores(kalman_history)
            else:
                kalman_obs = {
                    "rule_score":  rule_score,
                    "ml_score":    rule_score,
                    "survival_hi": model_b_out["health_index"] if model_b_out and not np.isnan(model_b_out.get("health_index", np.nan)) else DEFAULT_HI,
                    "mahal_hi":    model_c_out["health_index"] if model_c_out and not np.isnan(model_c_out.get("health_index", np.nan)) else DEFAULT_HI,
                }
                kalman_state = kalman.update(kalman_obs)

            # --- DST Fusion ---
            # Filter out None, NaN health_index, and Mahal placeholder outputs
            # (score_source "no_model"/"fallback" means <11 logs -- the returned
            # health_index=100 is a stub, not a real measurement; including it
            # would bias the fused score toward perfect health).
            valid_outputs = []
            for out in [model_a_out, model_b_out, model_c_out, model_e_out,
                        model_m_anomaly_out, model_m_rul_out]:
                if out is not None:
                    # Skip placeholder Mahal results
                    if out.get("score_source") in ("no_model", "fallback"):
                        continue
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
                    "pinn_rul":      model_a_out,
                    "survival":      model_b_out,
                    "mahal_hi":      model_c_out,
                    "anomaly":       model_e_out,
                    "moment_anomaly": model_m_anomaly_out,
                    "moment_rul":    model_m_rul_out,
                },
            })
        except Exception as _fusion_exc:
            logger.warning(f"DST fusion failed: {_fusion_exc}", exc_info=True)
            # Graceful fallback: unified_health_score mirrors P1 inversion
            base_result["unified_health_score"] = max(0.0, round(100.0 - failure_prob, 1))
            base_result["dst_verdict"] = risk_level.title()
            base_result["conflict_factor_K"] = 0.0
            base_result["score_source"] = "fallback_additive"

        # ==================== SHAP Explanations (P1) ====================
        # Skipped unless caller passes include_shap=True -- saves 50-200 ms per request.
        if not include_shap:
            base_result["shap_explanations"] = []
        else:
            try:
                from .xai_service import XAIService
                model_p1_raw = get_model()
                if model_p1_raw is not None:
                    # P1 expects 5 base features for SHAP (not 7 with derived features)
                    _p1_shap_features = [air, process, rpm, torque, wear]
                    _p1_feature_names = [
                        "Air temperature [K]",
                        "Process temperature [K]",
                        "Rotational speed [rpm]",
                        "Torque [Nm]",
                        "Tool wear [min]",
                    ]
                    base_result["shap_explanations"] = XAIService.explain_prediction(
                        model_p1_raw, _p1_shap_features, _p1_feature_names
                    )
                else:
                    base_result["shap_explanations"] = []
            except Exception as _xai_exc:
                logger.warning(f"SHAP explanations failed: {_xai_exc}", exc_info=True)
                base_result["shap_explanations"] = []

        return base_result
