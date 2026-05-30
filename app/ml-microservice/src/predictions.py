"""
ML Predictions Service
Provides P1-P6 prediction methods + DST unified health fusion (Wave 2).
"""
import logging
import numpy as np
from typing import List, Dict, Optional

from .core.config import config
from .core.feature_pipeline import FeaturePipeline, SensorReading
from .core.model_loader import load_p1, load_p2, load_p3, load_p4, load_p5, load_p6, load_p7
from .p7_parts_demand import survival_demand, croston_forecast, build_parts_demand
from .feature_store import FeatureStore
from .health_index import MahalanobisHealthIndex, get_health_index_model
from .survival_model import SurvivalModel, get_survival_model
from .anomaly_cusum import AnomalyEnsemble, get_anomaly_ensemble
from .kalman_estimator import KalmanStateEstimator, get_kalman_estimator
from .dst_fusion import DSTFusion, get_dst_fusion

logger = logging.getLogger(__name__)

try:
    from .pinn_rul import PINNRULEstimator, get_pinn_estimator
    _PINN_AVAILABLE = True
except ImportError:
    _PINN_AVAILABLE = False
    get_pinn_estimator = None

# TODO: MOMENT Foundation Model (model_m_anomaly, model_m_rul) is disabled.
# momentfm is not installed — outputs are excluded from the response entirely.
# To enable:
#   1. Add `momentfm` to requirements-heavy.txt
#   2. Rebuild the image: docker compose build ml-service
# Warning: image will be ~2 GB heavier and startup will be slower.
# Only worth enabling if MOMENT predictions are specifically needed.
#
# try:
#     from .moment_estimator import (
#         get_moment_anomaly_detector,
#         get_moment_rul_estimator,
#         MOMENT_AVAILABLE as _MOMENT_AVAILABLE,
#     )
# except ImportError:
#     _MOMENT_AVAILABLE = False
#     get_moment_anomaly_detector = None
#     get_moment_rul_estimator = None
_MOMENT_AVAILABLE = False
get_moment_anomaly_detector = None
get_moment_rul_estimator = None

# Thresholds for maintenance event detection
_WEAR_RESET_MAX_CURRENT = 10.0  # current wear must be < 10 to qualify as post-reset
_WEAR_RESET_MIN_HISTORY = 30.0  # at least one log in the look-back window must have had wear > 30
_WEAR_RESET_LOOKBACK    = 20    # how many recent logs to scan for prior high wear


def _detect_maintenance_event(logs: list, current_wear: float) -> bool:
    """
    Detect a tool-replacement / maintenance event from the log sequence.

    Returns True when:
      - current tool_wear < _WEAR_RESET_MAX_CURRENT (near-zero, i.e. tool was replaced)
      - AND any of the last _WEAR_RESET_LOOKBACK log entries had wear > _WEAR_RESET_MIN_HISTORY
        (machine was meaningfully worn recently — this is a reset, not a new machine)

    This catches both:
      - The exact transition step (first 0-wear reading after worn readings)
      - Subsequent 0-wear readings before the Mahal baseline adapts

    When True, Mahalanobis HI is excluded from DST fusion for this step.
    """
    if current_wear >= _WEAR_RESET_MAX_CURRENT:
        return False
    if len(logs) < 2:
        return False

    # Scan recent history (excluding latest entry) for high-wear readings
    lookback = logs[max(0, len(logs) - _WEAR_RESET_LOOKBACK - 1):-1]
    for lg in lookback:
        try:
            if float(lg.get("tool_wear", 0)) > _WEAR_RESET_MIN_HISTORY:
                return True
        except (TypeError, ValueError):
            continue
    return False


def failure_prob_to_risk(prob: float) -> str:
    """Map failure probability (0-100) to risk level string using config thresholds."""
    if prob >= config.p1_risk_critical:
        return "CRITICAL"
    if prob >= config.p1_risk_high:
        return "HIGH"
    if prob >= config.p1_risk_medium:
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
        model_p1 = load_p1()
        if model_p1 is None:
            return 0.0
        try:
            features_7 = features[:7] if len(features) >= 7 else features
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
        Args: [air, process, rpm, torque, wear, temp_delta, rpm_torque] (7 features)
        Returns: {TWF: {detected, probability}, HDF: {...}, etc.}
        """
        p2 = load_p2()
        if p2 is None:
            return {}
        model, labels = p2["model"], p2["labels"]
        try:
            input_data = [features]
            predictions = model.predict(input_data)[0]
            probabilities = [est.predict_proba(input_data)[0, 1] for est in model.estimators_]
            return {
                label: {"detected": bool(predictions[i]), "probability": round(float(probabilities[i]) * 100, 1)}
                for i, label in enumerate(labels)
            }
        except Exception:
            logger.warning("P2 failure type prediction failed", exc_info=True)
            return {}

    # ==================== P3: RUL Estimation ====================
    @staticmethod
    def predict_rul(features: List[float]) -> Optional[float]:
        """
        Predict Remaining Useful Life using P3 XGBoost.
        Args: [air, process, rpm, torque, wear, temp_delta, rpm_torque] (7 features)
        Returns: days until failure
        """
        model_p3 = load_p3()
        if model_p3 is None:
            return None
        try:
            pred_rul = model_p3.predict(np.array([features[:7]]))[0]
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
        p4 = load_p4()
        if p4 is None or p4.get("model") is None:
            return False, 0.0

        _ml_model_p4        = p4["model"]
        _p4_weights         = p4["weights"]
        _p4_thresholds      = p4["thresholds"]
        _p4_training_stats  = p4["training_stats"]
        _p4_ae_scaler       = p4["ae_scaler"]
        _p4_autoencoder     = p4["autoencoder"]
        _p4_feature_pipeline = p4.get("feature_pipeline")  # optional — None disables cluster deviation

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

            is_anomaly = ensemble_score > config.p4_anomaly_threshold
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
        Args: [air, process, rpm, torque, wear, temp_delta, rpm_torque] (7 features)
        Returns: priority level string
        """
        p5 = load_p5()
        if p5 is None:
            return "Medium"
        model, labels = p5["model"], p5["labels"]
        try:
            pred_idx = model.predict([features])[0]
            return labels[pred_idx]
        except Exception:
            logger.warning("P5 priority prediction failed", exc_info=True)
            return "Medium"

    # ==================== P6: Maintenance Schedule ====================
    @staticmethod
    def predict_maintenance_schedule(features: List[float]) -> float:
        """
        Predict optimal days to schedule maintenance using P6.
        Args: [air, process, rpm, torque, wear, temp_delta, rpm_torque] (7 features)
        Returns: days
        """
        model_p6 = load_p6()
        if model_p6 is None:
            return 7.0
        try:
            wear = float(features[4])
            tool_wear_sq = float(features[7]) if len(features) > 7 else wear ** 2
            features_8 = list(features[:7]) + [tool_wear_sq]
            days = model_p6.predict([features_8])[0]
            return max(0.0, float(days))
        except Exception:
            logger.warning("P6 maintenance schedule prediction failed", exc_info=True)
            return 7.0

    # ==================== P7: Parts Demand ====================
    @staticmethod
    def predict_parts_demand(
        machine_id: int,
        rul_days: float,
        failure_type_probs: Dict[str, float],
        horizon_days: int = 30,
    ) -> Dict:
        """
        Predict parts needed within the next horizon_days.
        Args:
            machine_id: machine identifier (for logging, future DB stock lookup)
            rul_days: remaining useful life estimate (days)
            failure_type_probs: {failure_type: probability 0-1}
            horizon_days: planning horizon (default 30 days)
        Returns: parts_demand contract {horizon_days, source, items:[...]}
        """
        m = load_p7()
        if m is None:
            return {"horizon_days": horizon_days, "source": "deterministic_fallback", "items": []}
        try:
            failure_part_map = m.get("failure_part_map", {})
            consumable_params = m.get("consumable_params", {})
            parts_catalog     = m.get("parts_catalog", {})
            theta             = m.get("meta", {}).get("theta", 0.05)

            # Survival-path demand from condition signals
            surv = survival_demand(
                failure_type_probs, rul_days, float(horizon_days),
                failure_part_map, theta=theta,
            )

            # Consumable-path demand from Croston forecasts (monthly series → horizon)
            cons: Dict = {}
            for pid, params in consumable_params.items():
                series = params.get("series", [])
                if series:
                    rate = croston_forecast(series)          # units per period (monthly)
                    cons[int(pid)] = rate * horizon_days / 30.0

            # Use parts_catalog as stock proxy (on_hand=0 until DB lookup wired in T8)
            stock = {pid: meta for pid, meta in parts_catalog.items()}

            return build_parts_demand(surv, cons, stock, horizon_days, "p7_model")
        except Exception:
            logger.warning("P7 parts demand prediction failed", exc_info=True)
            return {"horizon_days": horizon_days, "source": "deterministic_fallback", "items": []}

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
        air     = float(telemetry.get("air_temperature",    config.default_air_temp))
        process = float(telemetry.get("process_temperature", config.default_process_temp))
        rpm     = float(telemetry.get("rotational_speed",   config.default_rpm))
        torque  = float(telemetry.get("torque",             config.default_torque))
        wear    = float(telemetry.get("tool_wear",          config.default_tool_wear))

        reading    = SensorReading(air_temp=air, process_temp=process,
                                   rpm=rpm, torque=torque, tool_wear=wear)
        features_5 = FeaturePipeline.build_5(reading)
        features_7 = FeaturePipeline.build_7(reading)

        # Run all predictions
        failure_prob  = MachineLearningService.predict_failure_probability(features_7)
        failure_types = MachineLearningService.predict_failure_type(features_7)
        rul_days      = MachineLearningService.predict_rul(features_7)
        is_anomaly, anomaly_score = MachineLearningService.detect_anomaly(features_5)
        priority      = MachineLearningService.predict_priority(features_7)
        schedule_days = MachineLearningService.predict_maintenance_schedule(features_7)

        # P7: convert P2 probabilities (0-100) → 0-1 scale for survival math
        ft_probs: Dict[str, float] = {
            ft: v.get("probability", 0.0) / 100.0
            for ft, v in failure_types.items()
        } if failure_types else {}
        parts_demand = MachineLearningService.predict_parts_demand(
            machine_id=int(telemetry.get("machine_id", -1)),
            rul_days=float(rul_days) if rul_days is not None else 365.0,
            failure_type_probs=ft_probs,
            horizon_days=30,
        )

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
            "p7_parts_demand": parts_demand,
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

            # --- Model M: MOMENT Foundation Model (DISABLED) ---
            # momentfm not installed → outputs excluded from response.
            # TODO: To enable MOMENT predictions:
            #   1. Add `momentfm` to requirements-heavy.txt
            #   2. Rebuild: docker compose build ml-service
            #   3. Uncomment the import block at the top of this file
            #   4. Remove the _MOMENT_AVAILABLE = False override
            # Warning: ~2 GB heavier image, slower startup.
            # Only worth it if MOMENT predictions are specifically needed.
            #
            # if _MOMENT_AVAILABLE and len(logs) >= 3:
            #     try:
            #         detector = get_moment_anomaly_detector()
            #         if detector is not None:
            #             model_m_anomaly_out = detector.predict(logs)
            #     except Exception as _me:
            #         logger.warning(f"MOMENT anomaly failed: {_me}")
            #     try:
            #         rul_est = get_moment_rul_estimator()
            #         if rul_est is not None:
            #             model_m_rul_out = rul_est.predict(logs)
            #     except Exception as _me:
            #         logger.warning(f"MOMENT RUL failed: {_me}")

            # --- Maintenance event detection ---
            # If tool_wear is near-zero AND recent history had high wear, this is a
            # post-maintenance state (tool replaced). Mahalanobis distance will be
            # extreme because the baseline was fitted on high-wear data.
            # Exclude model_c_out from DST fusion until the baseline adapts.
            maintenance_event = _detect_maintenance_event(logs, wear)
            if maintenance_event:
                logger.info(
                    f"Maintenance event detected for machine {machine_id} "
                    f"(tool_wear={wear:.1f}, recent history had high wear). "
                    f"Excluding Mahalanobis HI + Anomaly CUSUM from DST fusion."
                )

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
            # Filter out None, NaN health_index, and Mahal placeholder outputs.
            # (score_source "no_model"/"fallback" means <11 logs -- the returned
            # health_index=100 is a stub, not a real measurement; including it
            # would bias the fused score toward perfect health).
            # On a maintenance event (tool replaced), both Mahal AND anomaly
            # CUSUM are excluded from DST fusion:
            #   - Mahal: dm2 spikes because baseline was fit on high-wear data
            #   - Anomaly CUSUM: all channels alarm on wear-reset; this is an
            #     artifact of the state change, not genuine degradation
            valid_outputs = []
            for out in [model_a_out, model_b_out, model_c_out, model_e_out]:
                if out is None:
                    continue
                # Skip placeholder Mahal results
                if out.get("score_source") in ("no_model", "fallback"):
                    continue
                # Skip Mahal + CUSUM anomaly on maintenance event (post tool-wear reset)
                if maintenance_event and out.get("model_id") in (
                    "model_c_mahal_hi", "model_e_anomaly"
                ):
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
                "maintenance_event":         maintenance_event,
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
                    # moment_anomaly and moment_rul omitted — momentfm not installed.
                    # See TODO above to re-enable.
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
                model_p1_raw = load_p1()
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
