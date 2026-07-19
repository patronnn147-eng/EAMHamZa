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

# MOMENT Foundation Model (model_m_anomaly, model_m_rul) is disabled.
# momentfm is not installed — outputs are excluded from the response entirely.
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


# ---------------------------------------------------------------------------
# Wave-2 private helpers — extracted to keep predict_all CC < 15
# ---------------------------------------------------------------------------

def _safe_hi(out: Optional[Dict], default: float = 75.0) -> float:
    """Return health_index from a model output dict, or default if missing/NaN."""
    if out is None:
        return default
    hi = out.get("health_index", np.nan)
    return hi if not np.isnan(hi) else default


def _parse_iso_ts(s: str):
    """Parse ISO timestamp string; return datetime or None on failure."""
    from datetime import datetime as _dt_cls
    if not s:
        return None
    try:
        return _dt_cls.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _p3_history_features(logs: list, machine_id: int,
                          current_process: float, current_torque: float,
                          current_rpm: float, current_wear: float) -> tuple:
    """P3-only engineered features: tool_wear velocity + rolling-5 means of
    process_temp/torque/rpm, matching ml_retraining.py's training-time
    computation (rolling window includes the current reading, min_periods=1
    so a machine with no history yet just gets its own instantaneous value —
    same defaults training uses for baseline ai4i2020.csv rows with no
    machine sequence). `logs` is telemetry_logs from the backend, already
    filtered to real (non-synthetic) data by _get_telemetry_history.
    """
    machine_logs = [lg for lg in logs if int(lg.get("machine_id", -1)) == machine_id]
    machine_logs.sort(key=lambda lg: str(lg.get("created_at", "")))
    recent_hist = machine_logs[-4:]  # up to 4 prior readings + current = window of 5

    prev_wear = float(recent_hist[-1].get("tool_wear", current_wear)) if recent_hist else current_wear
    velocity = current_wear - prev_wear

    proc_vals = [float(lg.get("process_temperature", current_process)) for lg in recent_hist] + [current_process]
    torque_vals = [float(lg.get("torque", current_torque)) for lg in recent_hist] + [current_torque]
    rpm_vals = [float(lg.get("rotational_speed", current_rpm)) for lg in recent_hist] + [current_rpm]

    return (
        velocity,
        sum(proc_vals) / len(proc_vals),
        sum(torque_vals) / len(torque_vals),
        sum(rpm_vals) / len(rpm_vals),
    )


def _run_model_c(hi_model, logs: list, features_5: list) -> Optional[Dict]:
    """Run Mahalanobis Health Index model; returns output dict or None."""
    if hi_model is None and len(logs) >= 2:
        hi_model = MahalanobisHealthIndex()
    if hi_model is None:
        return None
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
        return hi_model.fit_and_score_history(history_matrix)
    if hi_model._fitted:
        return hi_model.score(np.array(features_5))
    return None


def _run_model_e(anomaly_model, logs: list, features_5: list) -> Optional[Dict]:
    """Run anomaly ensemble model; returns output dict or None."""
    if anomaly_model is None or not anomaly_model._fitted:
        return None
    feature_names = [
        "air_temperature", "process_temperature",
        "rotational_speed", "torque", "tool_wear",
    ]
    history_arrays = [
        np.array([
            float(lg.get("air_temperature", 298)),
            float(lg.get("process_temperature", 308)),
            float(lg.get("rotational_speed", 1500)),
            float(lg.get("torque", 40)),
            float(lg.get("tool_wear", 0)),
        ])
        for lg in logs[:-1]
    ] if len(logs) > 1 else []
    return anomaly_model.predict_with_history(
        np.array(features_5), feature_names, history=history_arrays,
    )


def _run_model_b(logs: list, snapshot) -> Optional[Dict]:
    """Run survival model; returns output dict or None."""
    if len(logs) >= 10:
        local_surv = SurvivalModel()
        try:
            local_surv.fit_from_logs(logs)
            if local_surv._fitted:
                return local_surv.predict(snapshot)
        except Exception as _e:
            logger.warning(f"Survival fit_from_logs failed: {_e}")
        return None
    global_surv = get_survival_model()
    if global_surv is not None and global_surv._fitted:
        return global_surv.predict(snapshot)
    return None


def _run_model_a(time_series: list) -> Optional[Dict]:
    """Run PINN RUL estimator; returns output dict or None."""
    if not _PINN_AVAILABLE or len(time_series) < 3:
        return None
    pinn = get_pinn_estimator()
    if pinn is not None and pinn._fitted:
        return pinn.predict(time_series)
    return None


def _build_kalman_state(
    logs: list, model_b_out: Optional[Dict], model_c_out: Optional[Dict], rule_score: float
) -> Dict:
    """Build and update a per-request Kalman filter; returns kalman_state dict."""
    kalman = KalmanStateEstimator()
    if len(logs) < 2:
        obs = {
            "rule_score": rule_score,
            "ml_score": rule_score,
            "survival_hi": _safe_hi(model_b_out),
            "mahal_hi": _safe_hi(model_c_out),
        }
        return kalman.update(obs)

    kalman_history = []
    prev_ts = None
    for lg in logs[:-1]:
        air_h = float(lg.get("air_temperature", 298))
        hi_est = max(0.0, min(100.0, 100.0 - (air_h - 298) * 2.0))
        ts = _parse_iso_ts(lg.get("created_at", ""))
        if prev_ts is not None and ts is not None:
            elapsed_sec = (ts - prev_ts).total_seconds()
            dt_days = max(10 / 1440.0, min(30.0, elapsed_sec / 86400.0))
        else:
            dt_days = 1.0
        kalman_history.append({"rule_score": hi_est, "dt": dt_days})
        prev_ts = ts

    last_ts = _parse_iso_ts(logs[-1].get("created_at", "")) if logs else None
    if prev_ts is not None and last_ts is not None:
        elapsed_last = (last_ts - prev_ts).total_seconds()
        final_dt = max(10 / 1440.0, min(30.0, elapsed_last / 86400.0))
    else:
        final_dt = 1.0
    kalman_history.append({
        "rule_score": rule_score,
        "ml_score": rule_score,
        "survival_hi": _safe_hi(model_b_out),
        "mahal_hi": _safe_hi(model_c_out),
        "dt": final_dt,
    })
    return kalman.smooth_from_scores(kalman_history)


def _filter_dst_inputs(model_outputs: list, maintenance_event: bool) -> list:
    """Remove None, placeholder, and maintenance-event-tainted outputs."""
    excluded_on_maint = {"model_c_mahal_hi", "model_e_anomaly"}
    valid = []
    for out in model_outputs:
        if out is None:
            continue
        if out.get("score_source") in ("no_model", "fallback"):
            continue
        if maintenance_event and out.get("model_id") in excluded_on_maint:
            continue
        hi = out.get("health_index")
        if hi is not None and not np.isnan(hi):
            valid.append(out)
    return valid


def _run_shap_explanations(include_shap: bool, features_5: list) -> list:
    """Return SHAP explanation list; empty list if disabled or on error."""
    if not include_shap:
        return []
    try:
        from .xai_service import XAIService
        model_p1_raw = load_p1()
        if model_p1_raw is None:
            return []
        feature_names = [
            "Air temperature [K]",
            "Process temperature [K]",
            "Rotational speed [rpm]",
            "Torque [Nm]",
            "Tool wear [min]",
        ]
        return XAIService.explain_prediction(model_p1_raw, features_5, feature_names)
    except Exception as _xai_exc:
        logger.warning(f"SHAP explanations failed: {_xai_exc}", exc_info=True)
        return []


def _run_wave2(telemetry: Dict, features_5: list, failure_prob: float, risk_level: str) -> Dict:
    """Run Wave 2 DST fusion pipeline; returns dict to merge into base_result."""
    machine_id = int(telemetry.get("machine_id", -1))
    logs = telemetry.get("telemetry_logs", [])

    snapshot = FeatureStore.extract_full_snapshot(
        telemetry,
        context={
            "machine_id": machine_id,
            "days_since_maint": int(telemetry.get("days_since_maint", -1)),
            "open_work_orders": int(telemetry.get("open_work_orders", 0)),
            "recent_interventions": int(telemetry.get("recent_interventions", 0)),
            "machine_status": str(telemetry.get("machine_status", "OPERATIONNELLE")),
        },
    )
    time_series = FeatureStore.build_time_series_from_logs(machine_id, logs) if logs else []

    model_c_out = _run_model_c(get_health_index_model(), logs, features_5)
    model_e_out = _run_model_e(get_anomaly_ensemble(), logs, features_5)
    model_b_out = _run_model_b(logs, snapshot)
    model_a_out = _run_model_a(time_series)

    wear = float(telemetry.get("tool_wear", 0))
    maintenance_event = _detect_maintenance_event(logs, wear)
    if maintenance_event:
        logger.info(
            f"Maintenance event detected for machine {machine_id} "
            f"(tool_wear={wear:.1f}, recent history had high wear). "
            f"Excluding Mahalanobis HI + Anomaly CUSUM from DST fusion."
        )

    rule_score = max(0.0, 100.0 - failure_prob)
    kalman_state = _build_kalman_state(logs, model_b_out, model_c_out, rule_score)
    model_outputs = _filter_dst_inputs(
        [model_a_out, model_b_out, model_c_out, model_e_out], maintenance_event
    )
    fusion_result = get_dst_fusion().fuse(model_outputs, kalman_state)

    return {
        "unified_health_score": fusion_result["unified_health_score"],
        "dst_verdict": fusion_result["dst_verdict"],
        "conflict_factor_K": fusion_result["conflict_factor_K"],
        "dst_score": fusion_result["dst_score"],
        "kalman_hi": fusion_result["kalman_hi"],
        "kalman_rul": fusion_result["kalman_rul"],
        "sensor_fault_flag": fusion_result["sensor_fault_flag"],
        "model_disagreement_alert": fusion_result["model_disagreement_alert"],
        "maintenance_event": maintenance_event,
        "bpa": {
            "healthy": fusion_result["bpa_healthy"],
            "degrading": fusion_result["bpa_degrading"],
            "critical": fusion_result["bpa_critical"],
            "unknown": fusion_result["bpa_unknown"],
        },
        "model_outputs": {
            "pinn_rul": model_a_out,
            "survival": model_b_out,
            "mahal_hi": model_c_out,
            "anomaly": model_e_out,
        },
    }


def _p4_norm(name: str, raw: float, thresholds: dict) -> float:
    """Normalise a P4 component score to [0, 1] using training min/max thresholds."""
    lo = thresholds.get(f'{name}_min', 0.0)
    hi = thresholds.get(f'{name}_max', 1.0)
    if hi == lo:
        return 0.5
    return float(np.clip((raw - lo) / (hi - lo), 0.0, 1.0))


def _p4_collect_components(p4: dict, x5, scores: dict, weights: dict) -> None:
    """Populate component_scores/weights dicts in-place for each available P4 detector."""
    model = p4["model"]
    p4w = p4["weights"]
    # 1. Isolation Forest (always available)
    scores['if'] = float(-model.decision_function(x5)[0])
    weights['if'] = p4w.get('if', 0.30)
    # 2. Autoencoder (optional)
    ae, scaler = p4.get("autoencoder"), p4.get("ae_scaler")
    if ae is not None and scaler is not None:
        try:
            x_s = scaler.transform(x5)
            ae_raw = float(np.mean((x_s - ae.predict(x_s, verbose=0)) ** 2))
            scores['ae'] = ae_raw
            weights['ae'] = p4w.get('ae', 0.40)
        except Exception:
            pass
    # 3. Z-Score
    t_mean, t_std = p4["training_stats"].get('mean'), p4["training_stats"].get('std')
    if t_mean and t_std:
        std_arr = np.array(t_std)
        std_arr[std_arr == 0] = 1.0
        scores['zscore'] = float(np.max(np.abs((x5[0] - np.array(t_mean)) / std_arr)))
        weights['zscore'] = p4w.get('zscore', 0.20)
    # 4. Cluster Deviation (optional)
    fp = p4.get("feature_pipeline")
    if fp is not None:
        try:
            import pandas as pd
            SENSOR_COLS = ['Air temperature [K]', 'Process temperature [K]', 'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]']
            x_v3 = fp.transform(pd.DataFrame(x5, columns=SENSOR_COLS))
            if hasattr(x_v3, 'columns') and 'cluster_distance' in x_v3.columns:
                scores['cluster'] = float(x_v3['cluster_distance'].values[0])
                weights['cluster'] = p4w.get('cluster', 0.10)
        except Exception:
            pass


def _p4_if_fallback(model, features: list) -> tuple:
    """Bare IF fallback when full P4 ensemble fails."""
    try:
        x_fb = np.array(features[:5]).reshape(1, -1)
        pred = model.predict(x_fb)[0]
        score = float(-model.decision_function(x_fb)[0])
        return bool(pred == -1), round(score, 4)
    except Exception:
        return False, 0.0


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
        Args: [air, process, rpm, torque, wear, temp_delta, rpm_torque] (7 base
        features) + optionally [tool_wear_velocity, process_temp_roll5_mean,
        torque_roll5_mean, rpm_roll5_mean] (11 total once P3 has been
        retrained with the extended set). Slices to whatever the loaded
        model actually expects (model.n_features_in_) rather than a
        hardcoded count, so this stays correct across both the current
        7-feature pkl and any future retrain with more features.
        Returns: days until failure
        """
        model_p3 = load_p3()
        if model_p3 is None:
            return None
        try:
            n = getattr(model_p3, "n_features_in_", 7)
            pred_rul = model_p3.predict(np.array([features[:n]]))[0]
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

        _ml_model_p4 = p4["model"]
        try:
            x5 = np.array(features[:5], dtype=float).reshape(1, -1)
            component_scores: dict = {}
            component_weights: dict = {}
            _p4_collect_components(p4, x5, component_scores, component_weights)
            total_weight = sum(component_weights.values())
            if total_weight == 0:
                return False, 0.0
            thresholds = p4["thresholds"]
            ensemble_score = sum(
                _p4_norm(name, score, thresholds) * component_weights[name]
                for name, score in component_scores.items()
            ) / total_weight
            is_anomaly = ensemble_score > config.p4_anomaly_threshold
            return is_anomaly, round(ensemble_score, 4)
        except Exception:
            logger.warning("P4 anomaly detection failed", exc_info=True)
            return _p4_if_fallback(_ml_model_p4, features)

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
            stock = dict(parts_catalog)

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
        air     = float(telemetry.get("air_temperature",    config.default_air_temp))
        process = float(telemetry.get("process_temperature", config.default_process_temp))
        rpm     = float(telemetry.get("rotational_speed",   config.default_rpm))
        torque  = float(telemetry.get("torque",             config.default_torque))
        wear    = float(telemetry.get("tool_wear",          config.default_tool_wear))

        reading    = SensorReading(air_temp=air, process_temp=process,
                                   rpm=rpm, torque=torque, tool_wear=wear)
        features_5 = FeaturePipeline.build_5(reading)
        features_7 = FeaturePipeline.build_7(reading)

        # P3-only: append velocity + rolling-5 means computed from real
        # telemetry history (if any). predict_rul() slices to however many
        # features the loaded model actually expects, so this is a no-op
        # against the current 7-feature pkl and only activates once P3 is
        # retrained with the extended feature set.
        _velocity, _proc_mean, _torque_mean, _rpm_mean = _p3_history_features(
            telemetry.get("telemetry_logs", []), int(telemetry.get("machine_id", -1)),
            process, torque, rpm, wear,
        )
        features_11 = features_7 + [_velocity, _proc_mean, _torque_mean, _rpm_mean]

        # Wave 1: P1-P7 predictions
        failure_prob  = MachineLearningService.predict_failure_probability(features_7)
        failure_types = MachineLearningService.predict_failure_type(features_7)
        rul_days      = MachineLearningService.predict_rul(features_11)
        is_anomaly, anomaly_score = MachineLearningService.detect_anomaly(features_5)
        priority      = MachineLearningService.predict_priority(features_7)
        schedule_days = MachineLearningService.predict_maintenance_schedule(features_7)

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

        # Wave 2: DST fusion pipeline
        try:
            base_result.update(_run_wave2(telemetry, features_5, failure_prob, risk_level))
        except Exception as _fusion_exc:
            logger.warning(f"DST fusion failed: {_fusion_exc}", exc_info=True)
            base_result["unified_health_score"] = max(0.0, round(100.0 - failure_prob, 1))
            base_result["dst_verdict"] = risk_level.title()
            base_result["conflict_factor_K"] = 0.0
            base_result["score_source"] = "fallback_additive"

        base_result["shap_explanations"] = _run_shap_explanations(
            include_shap, [air, process, rpm, torque, wear]
        )
        return base_result
