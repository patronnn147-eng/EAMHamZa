"""
ML Model Loader - Adapted for Microservice
Loads trained .pkl models at startup
"""

import os
import joblib
import logging
import warnings

# Suppress sklearn minor-version mismatch warnings (models may have been
# trained with a slightly different sklearn patch; they still work fine).
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

logger = logging.getLogger(__name__)

# Get the models directory (relative to this file)
MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")


def _extract_model(data, model_key: str = "model"):
    """
    Defensively extract model from pkl data.

    All pkl files are saved as dicts:
        {'model': actual_sklearn/xgb_object, 'features': [...], 'metrics': {...}, ...}

    P2 and P5 already used this pattern correctly.  This helper applies the
    same logic to P1, P3, P4, and P6 so every loader is consistent.
    Falls back to returning data as-is for any legacy pkl saved as a bare model.
    """
    if isinstance(data, dict):
        return data.get(model_key)
    return data  # legacy bare-model format


# ==================== P1: Failure Probability Model ====================
_MODEL = None
_MODEL_PATH = os.path.join(MODELS_DIR, "basic_machine_model.pkl")


def get_model():
    """Get P1 failure probability model (lazy loading)."""
    global _MODEL
    if _MODEL is None and os.path.exists(_MODEL_PATH):
        try:
            data = joblib.load(_MODEL_PATH)
            _MODEL = _extract_model(data)
            logger.info(f"[OK] P1 model loaded from {_MODEL_PATH}")
        except Exception as e:
            logger.exception(f"[ERROR] Failed to load P1 model: {e}")
    return _MODEL


# ==================== P2: Failure Type Model ====================
P2_MODEL_PATH = os.path.join(MODELS_DIR, "ml_model_p2_failure_type.pkl")
try:
    _ml_model_p2_data = joblib.load(P2_MODEL_PATH)
    _ml_model_p2 = _ml_model_p2_data["model"]
    _p2_features = _ml_model_p2_data.get("features")
    _p2_labels = _ml_model_p2_data.get("labels")
    logger.info(f"[OK] P2 model loaded from {P2_MODEL_PATH}")
except Exception as e:
    logger.warning(f"[WARN] Failed to load P2 model: {e}")
    _ml_model_p2 = None
    _p2_features = None
    _p2_labels = None


# ==================== P3: RUL Estimation Model ====================
P3_MODEL_PATH = os.path.join(MODELS_DIR, "ml_model_p3_rul.pkl")
try:
    _p3_data = joblib.load(P3_MODEL_PATH)
    _ml_model_p3 = _extract_model(_p3_data)
    logger.info(f"[OK] P3 model loaded from {P3_MODEL_PATH}")
except Exception as e:
    logger.warning(f"[WARN] Failed to load P3 model: {e}")
    _ml_model_p3 = None


# ==================== P5: Work Order Priority Model ====================
P5_MODEL_PATH = os.path.join(MODELS_DIR, "ml_model_p5_priority.pkl")
try:
    _ml_model_p5_data = joblib.load(P5_MODEL_PATH)
    _ml_model_p5 = _ml_model_p5_data["model"]
    _p5_labels = _ml_model_p5_data["labels"]
    logger.info(f"[OK] P5 model loaded from {P5_MODEL_PATH}")
except Exception as e:
    logger.warning(f"[WARN] Failed to load P5 model: {e}")
    _ml_model_p5 = None
    _p5_labels = None


# ==================== P4: Anomaly Detection (Ensemble v2) ====================
_P4_V2_PATH = os.path.join(MODELS_DIR, "ml_model_p4_anomaly_v2.pkl")
_P4_V1_PATH = os.path.join(MODELS_DIR, "ml_model_p4_anomaly.pkl")

_ml_model_p4 = None  # IsolationForest (always available)
_p4_weights = {"ae": 0.40, "if": 0.30, "zscore": 0.20, "cluster": 0.10}
_p4_thresholds = {}
_p4_training_stats = {}  # {'mean': [...], 'std': [...]}
_p4_ae_scaler = None
_p4_autoencoder = None  # optional — requires TensorFlow
_p4_feature_pipeline = None  # optional — for cluster deviation
_p4_ensemble_type = "isolation_forest"

_p4_path = _P4_V2_PATH if os.path.exists(_P4_V2_PATH) else _P4_V1_PATH
try:
    _p4_raw = joblib.load(_p4_path)
    if isinstance(_p4_raw, dict) and "iso_model" in _p4_raw:
        # v2 ensemble dict from p4_anomaly_ensemble.ipynb
        _ml_model_p4 = _p4_raw["iso_model"]
        _p4_weights = _p4_raw.get("weights", _p4_weights)
        _p4_thresholds = _p4_raw.get("thresholds", {})
        _p4_training_stats = _p4_raw.get("training_stats", {})
        _p4_ae_scaler = _p4_raw.get("ae_scaler")
        _p4_ensemble_type = _p4_raw.get("type", "anomaly_ensemble_v2")

        # Optional: load autoencoder (needs TensorFlow)
        ae_path = _p4_raw.get("autoencoder_path")
        if ae_path and os.path.exists(ae_path):
            try:
                import tensorflow as tf  # noqa: F401

                _p4_autoencoder = tf.keras.models.load_model(ae_path)
                logger.info("[OK] P4 autoencoder loaded (TF available)")
            except ImportError:
                logger.info("[INFO] P4 autoencoder skipped — TensorFlow not installed")
            except Exception as _ae_err:
                logger.warning(f"[WARN] P4 autoencoder load failed: {_ae_err}")

        # Optional: feature pipeline for cluster deviation
        _pipeline_path = os.path.join(MODELS_DIR, "feature_pipeline_v3.pkl")
        if os.path.exists(_pipeline_path):
            try:
                _p4_feature_pipeline = joblib.load(_pipeline_path)
                logger.info(
                    "[OK] P4 feature pipeline loaded (cluster deviation enabled)"
                )
            except Exception as _pe:
                logger.warning(f"[WARN] P4 feature pipeline load failed: {_pe}")

        logger.info(
            f"[OK] P4 ensemble loaded from {_p4_path} (type={_p4_ensemble_type})"
        )
    else:
        # Legacy bare model or v1 dict — fall back to simple IF
        _ml_model_p4 = _extract_model(_p4_raw)
        _p4_ensemble_type = "isolation_forest"
        logger.info(f"[OK] P4 legacy IF loaded from {_p4_path}")
except Exception as e:
    logger.warning(f"[WARN] Failed to load P4 model: {e}")


# ==================== P6: Maintenance Schedule Model ====================
P6_MODEL_PATH = os.path.join(MODELS_DIR, "ml_model_p6_schedule.pkl")
try:
    _p6_data = joblib.load(P6_MODEL_PATH)
    _ml_model_p6 = _extract_model(_p6_data)
    logger.info(f"[OK] P6 model loaded from {P6_MODEL_PATH}")
except Exception as e:
    logger.warning(f"[WARN] Failed to load P6 model: {e}")
    _ml_model_p6 = None


def get_all_models_status():
    """Get status of all models."""
    return {
        "p1_failure": {"loaded": get_model() is not None},
        "p2_failure_type": {"loaded": _ml_model_p2 is not None},
        "p3_rul": {"loaded": _ml_model_p3 is not None},
        "p4_anomaly": {
            "loaded": _ml_model_p4 is not None,
            "type": _p4_ensemble_type,
            "autoencoder": _p4_autoencoder is not None,
            "cluster": _p4_feature_pipeline is not None,
        },
        "p5_priority": {"loaded": _ml_model_p5 is not None},
        "p6_schedule": {"loaded": _ml_model_p6 is not None},
    }
