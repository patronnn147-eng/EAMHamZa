"""
Model M: MOMENT Foundation Model for Time Series
Wraps AutonLab/MOMENT-1-large for:
  - Anomaly detection on the 5-sensor telemetry sequence
  - Short-horizon forecasting to derive a degradation-based RUL estimate

Requires: pip install momentfm torch

Pattern mirrors pinn_rul.py — optional import guard so the service starts
even if momentfm / torch are not installed.
"""
import logging
import numpy as np
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Optional import guard (same pattern as pinn_rul.py)
# -----------------------------------------------------------------------
try:
    import torch
    from momentfm import MOMENTPipeline
    MOMENT_AVAILABLE = True
except ImportError:
    MOMENT_AVAILABLE = False
    logger.warning("momentfm not installed — MOMENT model disabled. "
                   "Run: pip install momentfm")

# MOMENT was pre-trained with a fixed context length of 512 timesteps
MOMENT_SEQ_LEN = 512
# Number of sensor channels we feed it
N_CHANNELS = 5   # [air_temperature, process_temperature, rotational_speed, torque, tool_wear]
# How many future steps to forecast (used for RUL estimation)
FORECAST_HORIZON = 32


# -----------------------------------------------------------------------
# Helper: build a (1, N_CHANNELS, MOMENT_SEQ_LEN) tensor from logs
# -----------------------------------------------------------------------

def _logs_to_tensor(logs: List[Dict]) -> "torch.Tensor":
    """
    Convert telemetry log dicts → float32 tensor of shape
    (1, N_CHANNELS, MOMENT_SEQ_LEN).

    If fewer than MOMENT_SEQ_LEN entries, the sequence is left-padded
    with the first known value (forward fill from the earliest reading).
    If more, only the most recent MOMENT_SEQ_LEN entries are used.
    """
    keys = ["air_temperature", "process_temperature",
            "rotational_speed", "torque", "tool_wear"]
    defaults = [298.0, 308.0, 1500.0, 40.0, 0.0]

    rows = []
    for lg in logs:
        rows.append([float(lg.get(k, d)) for k, d in zip(keys, defaults)])

    arr = np.array(rows, dtype=np.float32)       # (T, 5)

    # Truncate to last MOMENT_SEQ_LEN steps
    if len(arr) > MOMENT_SEQ_LEN:
        arr = arr[-MOMENT_SEQ_LEN:]

    # Pad on the left if shorter
    if len(arr) < MOMENT_SEQ_LEN:
        pad = np.tile(arr[0], (MOMENT_SEQ_LEN - len(arr), 1))
        arr = np.vstack([pad, arr])

    # (T, C) → (C, T) → (1, C, T)
    tensor = torch.from_numpy(arr.T).unsqueeze(0)
    return tensor


# -----------------------------------------------------------------------
# Normalisation (channel-wise z-score, avoids MOMENT scale sensitivity)
# -----------------------------------------------------------------------

def _normalise(tensor: "torch.Tensor"):
    """Return (normalised_tensor, mean, std) — all per-channel."""
    # tensor: (1, C, T)
    mean = tensor.mean(dim=-1, keepdim=True)   # (1, C, 1)
    std  = tensor.std(dim=-1, keepdim=True).clamp(min=1e-6)
    return (tensor - mean) / std, mean, std


# -----------------------------------------------------------------------
# MOMENTAnomalyDetector
# -----------------------------------------------------------------------

class MOMENTAnomalyDetector:
    """
    Wraps MOMENT in anomaly_detection mode.

    MOMENT reconstructs the input sequence; large reconstruction error
    indicates anomaly. We convert the per-channel MSE into a single
    health-index score (100 = healthy, 0 = extreme anomaly).
    """

    def __init__(self):
        self._model = None
        self._fitted = False   # mirrors the _fitted convention in other models

    def load(self, model_name: str = "AutonLab/MOMENT-1-large") -> "MOMENTAnomalyDetector":
        """Download / cache the model from HuggingFace Hub."""
        if not MOMENT_AVAILABLE:
            raise RuntimeError("momentfm not installed")
        logger.info(f"Loading MOMENT anomaly model from {model_name} ...")
        self._model = MOMENTPipeline.from_pretrained(
            model_name,
            model_kwargs={"task_name": "reconstruction"},
        )
        self._model.init()
        self._model.eval()
        self._fitted = True
        logger.info("MOMENT anomaly model loaded.")
        return self

    def predict(self, logs: List[Dict]) -> Dict:
        """
        Score a telemetry log sequence for anomalies.

        Args:
            logs: list of telemetry dicts, oldest first.
                  Each dict has keys: air_temperature, process_temperature,
                  rotational_speed, torque, tool_wear.

        Returns:
            ModelOutput-compatible dict:
                model_id, health_index (0-100), critical_prob (0-1),
                rul_estimate (None), uncertainty, confidence,
                is_anomaly (bool), anomaly_score (float),
                reconstruction_mse (float)
        """
        if not self._fitted or self._model is None:
            raise RuntimeError("Call load() first")

        tensor = _logs_to_tensor(logs)                 # (1, C, 512)
        normed, _, _ = _normalise(tensor)
        input_mask = torch.ones(1, MOMENT_SEQ_LEN)    # all timesteps observed

        with torch.no_grad():
            output = self._model(normed, input_mask=input_mask)

        # output.reconstruction: (1, C, T) — MOMENT reconstructs the input
        # anomaly score = per-timestep MSE across channels
        reconstruction = output.reconstruction         # (1, C, T)
        scores = ((normed - reconstruction) ** 2).mean(dim=1).squeeze(0).detach().numpy()  # (T,)

        # Focus on the most recent half of the window (the newest data)
        recent_scores = scores[MOMENT_SEQ_LEN // 2:]
        mse = float(np.mean(recent_scores ** 2))

        # Convert MSE → health index: sigmoid-based mapping
        # mse=0 → HI=100, mse→∞ → HI→0
        hi = float(100.0 / (1.0 + 10.0 * mse))
        hi = max(0.0, min(100.0, hi))

        critical_prob = 1.0 - (hi / 100.0)
        is_anomaly = hi < 40.0

        return {
            "model_id":           "model_m_moment_anomaly",
            "health_index":       round(hi, 2),
            "critical_prob":      round(critical_prob, 4),
            "rul_estimate":       None,
            "uncertainty":        float(np.std(recent_scores)),
            "confidence":         0.85,
            "is_anomaly":         bool(is_anomaly),
            "anomaly_score":      round(float(np.max(np.abs(recent_scores))), 4),
            "reconstruction_mse": round(mse, 6),
        }


# -----------------------------------------------------------------------
# MOMENTRULEstimator
# -----------------------------------------------------------------------

class MOMENTRULEstimator:
    """
    Wraps MOMENT in forecasting mode to derive a degradation-based RUL.

    Strategy:
      1. Forecast the next FORECAST_HORIZON timesteps for each sensor.
      2. Compute tool_wear trend slope over the forecast window.
      3. Extrapolate how many steps until tool_wear hits a critical threshold
         (default: 250 min, ~83% of the 300-min max).
      4. Convert steps → days using the observed log cadence.
    """

    TOOL_WEAR_CRITICAL = 250   # minutes — treat as failure threshold
    CHANNEL_TOOL_WEAR  = 4     # index in the 5-feature vector

    def __init__(self):
        self._model = None
        self._fitted = False

    def load(self, model_name: str = "AutonLab/MOMENT-1-large") -> "MOMENTRULEstimator":
        """Download / cache the model from HuggingFace Hub."""
        if not MOMENT_AVAILABLE:
            raise RuntimeError("momentfm not installed")
        logger.info(f"Loading MOMENT forecasting model from {model_name} ...")
        self._model = MOMENTPipeline.from_pretrained(
            model_name,
            model_kwargs={
                "task_name":        "forecasting",
                "forecast_horizon": FORECAST_HORIZON,
            },
        )
        self._model.init()
        self._model.eval()
        self._fitted = True
        logger.info("MOMENT forecasting model loaded.")
        return self

    def predict(self, logs: List[Dict]) -> Dict:
        """
        Estimate RUL from telemetry history.

        Args:
            logs: list of telemetry dicts, oldest first (same format as anomaly).

        Returns:
            ModelOutput-compatible dict:
                model_id, health_index, critical_prob,
                rul_estimate (days), uncertainty, confidence
        """
        if not self._fitted or self._model is None:
            raise RuntimeError("Call load() first")

        tensor = _logs_to_tensor(logs)                 # (1, C, 512)
        normed, mean, std = _normalise(tensor)
        input_mask = torch.ones(1, MOMENT_SEQ_LEN)    # all timesteps observed

        with torch.no_grad():
            output = self._model(normed, input_mask=input_mask)

        # output.forecast: (1, forecast_horizon, C)  — normalised scale
        forecast_normed = output.forecast.squeeze(0).detach().numpy()  # (H, C)

        # De-normalise the tool_wear channel
        tw_mean = float(mean[0, self.CHANNEL_TOOL_WEAR, 0])
        tw_std  = float(std[0,  self.CHANNEL_TOOL_WEAR, 0])
        forecast_tw = forecast_normed[:, self.CHANNEL_TOOL_WEAR] * tw_std + tw_mean

        # Current tool_wear from latest log entry
        current_tw = float(logs[-1].get("tool_wear", 0)) if logs else 0.0

        # Estimate cadence: seconds between log entries → convert to days
        cadence_days = self._estimate_cadence_days(logs)

        # Linear extrapolation of tool_wear to critical threshold
        slope = float(np.polyfit(np.arange(len(forecast_tw)), forecast_tw, 1)[0])
        if slope <= 0:
            rul_steps = float("inf")
        else:
            remaining_wear = max(0.0, self.TOOL_WEAR_CRITICAL - current_tw)
            rul_steps = remaining_wear / slope

        rul_days = min(float(rul_steps * cadence_days), 365.0)

        # Health index: fraction of useful life remaining
        hi = max(0.0, min(100.0, 100.0 * (1.0 - current_tw / self.TOOL_WEAR_CRITICAL)))

        return {
            "model_id":      "model_m_moment_rul",
            "health_index":  round(hi, 2),
            "critical_prob": round(1.0 - hi / 100.0, 4),
            "rul_estimate":  round(rul_days, 1),
            "uncertainty":   round(float(np.std(forecast_tw)), 2),
            "confidence":    0.80,
            "forecast_tool_wear": [round(float(v), 1) for v in forecast_tw],
            "wear_slope_per_step": round(slope, 4),
        }

    @staticmethod
    def _estimate_cadence_days(logs: List[Dict]) -> float:
        """Try to infer hours between log entries; default 1/24 (hourly)."""
        if len(logs) >= 2:
            try:
                from datetime import datetime
                t0 = datetime.fromisoformat(str(logs[0].get("recorded_at", "")))
                t1 = datetime.fromisoformat(str(logs[-1].get("recorded_at", "")))
                total_days = (t1 - t0).total_seconds() / 86400.0
                cadence = total_days / max(1, len(logs) - 1)
                return max(cadence, 1 / 24 / 60)   # floor at 1 minute
            except Exception:
                pass
        return 1.0 / 24.0   # fallback: assume hourly readings


# -----------------------------------------------------------------------
# Module-level singletons (lazy load — only downloaded on first request)
# -----------------------------------------------------------------------

_moment_anomaly: Optional[MOMENTAnomalyDetector] = None
_moment_rul:     Optional[MOMENTRULEstimator]     = None


def get_moment_anomaly_detector() -> Optional[MOMENTAnomalyDetector]:
    """Return (and lazily load) the MOMENT anomaly singleton."""
    global _moment_anomaly
    if not MOMENT_AVAILABLE:
        return None
    if _moment_anomaly is None:
        try:
            _moment_anomaly = MOMENTAnomalyDetector().load()
        except Exception as e:
            logger.error(f"Failed to load MOMENT anomaly model: {e}")
            return None
    return _moment_anomaly


def get_moment_rul_estimator() -> Optional[MOMENTRULEstimator]:
    """Return (and lazily load) the MOMENT RUL singleton."""
    global _moment_rul
    if not MOMENT_AVAILABLE:
        return None
    if _moment_rul is None:
        try:
            _moment_rul = MOMENTRULEstimator().load()
        except Exception as e:
            logger.error(f"Failed to load MOMENT RUL model: {e}")
            return None
    return _moment_rul
