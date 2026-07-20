from functools import lru_cache
from pathlib import Path
import joblib
import logging
import os
from .config import config

logger = logging.getLogger(__name__)


def _extract(data, key: str = "model"):
    """Extract model from pkl dict, or return bare model for legacy pkls."""
    if isinstance(data, dict):
        return data.get(key)
    return data


def _load(path: Path, label: str):
    """Safe load — returns None on any failure."""
    if not path.exists():
        logger.error(f"[MISSING] {label} pkl not found: {path}")
        return None
    try:
        return joblib.load(path)
    except Exception as e:
        logger.exception(f"[ERROR] {label} pkl failed to load: {e}")
        return None


@lru_cache(maxsize=1)
def load_p1():
    data = _load(config.models_dir / "basic_machine_model.pkl", "P1")
    return _extract(data)


@lru_cache(maxsize=1)
def load_p2():
    data = _load(config.models_dir / "ml_model_p2_failure_type.pkl", "P2")
    if data is None:
        return None
    return {"model": data["model"], "labels": data.get("labels", [])}


@lru_cache(maxsize=1)
def load_p3():
    data = _load(config.models_dir / "ml_model_p3_rul.pkl", "P3")
    return _extract(data)


def _load_p4_autoencoder(data: dict):
    """Lazy-load the P4 autoencoder from its own .keras file (Phase 4.3).

    The AE is never embedded in the joblib pkl — TF/Keras model objects
    don't survive joblib round-trips reliably across versions — it's saved
    separately by the training script and referenced by filename, mirroring
    how p4_anomaly_ensemble.ipynb always intended this to work (see the
    legacy src/model_loader.py, which already had this exact logic; this
    was the missing half of the "real bug" found in Phase 4.3 — this
    authoritative loader was still reading a nonexistent embedded
    "autoencoder" key instead of resolving autoencoder_path).
    Returns None (not an error) whenever TF isn't installed or no AE was
    ever trained for this pkl — detect_anomaly()'s weight-renormalization
    already handles a missing AE component gracefully.
    """
    ae_filename = data.get("autoencoder_path")
    if not ae_filename:
        return None
    ae_path = config.models_dir / os.path.basename(ae_filename)
    if not ae_path.exists():
        logger.warning(f"[WARN] P4 autoencoder file missing: {ae_path}")
        return None
    try:
        import tensorflow as tf  # noqa: F401  (local import — optional heavy dep)

        model = tf.keras.models.load_model(str(ae_path))
        logger.info("[OK] P4 autoencoder loaded (TF available)")
        return model
    except ImportError:
        logger.info("[INFO] P4 autoencoder skipped — TensorFlow not installed")
        return None
    except Exception as ae_err:
        logger.warning(f"[WARN] P4 autoencoder load failed: {ae_err}")
        return None


@lru_cache(maxsize=1)
def load_p4():
    data = _load(config.models_dir / "ml_model_p4_anomaly_v2.pkl", "P4")
    if data is None:
        return None
    return {
        "model": data.get("iso_model"),
        "weights": data.get("weights", {}),
        "thresholds": data.get("thresholds", {}),
        "training_stats": data.get("training_stats", {}),
        "ae_scaler": data.get("ae_scaler"),
        "autoencoder": _load_p4_autoencoder(data),
    }


@lru_cache(maxsize=1)
def load_p3_quantile():
    """P3 prediction-interval heads (10th/50th/90th percentile), if the
    loaded pkl was retrained with them (Phase 4.2 addition — older pkls
    won't have this key, callers must treat None as 'no interval available'
    rather than an error)."""
    data = _load(config.models_dir / "ml_model_p3_rul.pkl", "P3-quantile")
    if not isinstance(data, dict) or data.get("quantile_model") is None:
        return None
    return {"model": data["quantile_model"], "levels": data.get("quantile_levels", [0.1, 0.5, 0.9])}


@lru_cache(maxsize=1)
def load_p5():
    data = _load(config.models_dir / "ml_model_p5_priority.pkl", "P5")
    if data is None:
        return None
    return {"model": data["model"], "labels": data.get("labels", [])}


@lru_cache(maxsize=1)
def load_p6():
    data = _load(config.models_dir / "ml_model_p6_schedule.pkl", "P6")
    return _extract(data)


@lru_cache(maxsize=1)
def load_p7():
    """P7 parts-demand model: dict {failure_part_map, consumable_params, meta}.
    Returns the whole dict (NOT _extract). None if pkl missing."""
    return _load(config.models_dir / "ml_model_p7_parts_demand.pkl", "P7")


def get_all_models_status():
    """Get status of all models as dict."""
    return {
        "p1_failure": {"loaded": load_p1() is not None},
        "p2_failure_type": {"loaded": load_p2() is not None},
        "p3_rul": {"loaded": load_p3() is not None},
        "p4_anomaly": {"loaded": load_p4() is not None},
        "p5_priority": {"loaded": load_p5() is not None},
        "p6_schedule": {"loaded": load_p6() is not None},
        "p7_parts_demand": {"loaded": load_p7() is not None},
    }


def startup_check():
    """Call at service startup. Logs OK/MISSING status of all models."""
    for name, fn in [
        ("P1", load_p1),
        ("P2", load_p2),
        ("P3", load_p3),
        ("P4", load_p4),
        ("P5", load_p5),
        ("P6", load_p6),
        ("P7", load_p7),
    ]:
        result = fn()
        status = "OK" if result is not None else "MISSING"
        logger.info(f"[{status}] {name} model")
