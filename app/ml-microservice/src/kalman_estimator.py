"""
Model F: Linear Kalman Filter State Estimator
Smooths health state [HI, RUL, degradation_rate] from noisy multi-model observations.
Treats each model output as a noisy measurement, automatically weighted by noise covariance.
Supports missing observations (NaN masking) and variable time steps (dt).

State: x = [HI, RUL, degradation_rate]

Transition model (dt = elapsed days since last observation):
    HI_t    = HI_{t-1}   - degradation_rate * dt   (health degrades at rate * elapsed_time)
    RUL_t   = RUL_{t-1}  - dt                       (remaining life decreases by elapsed time)
    rate_t  = rate_{t-1}                             (degradation rate held constant)

Why variable dt matters:
    Burst requests or irregular sensor cadence mean steps are NOT uniformly 1 day apart.
    Hardcoding dt=1 causes RUL to drain N days for N requests regardless of real elapsed time.
    Pass dt (days) per step; default=1.0 preserves backward-compat for daily cadence.
"""
import logging
import numpy as np
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# State dimension: [HI, RUL, degradation_rate]
STATE_DIM = 3
# Observation dimension: [rule_score, ml_score, survival_hi, mahal_hi]
OBS_DIM = 4

# Base transition matrix (dt=1.0, for reference only).
# update() always builds F_dt dynamically — do NOT use this directly.
#   Row 0: HI_t    = HI_{t-1} - 1.0 * rate
#   Row 1: RUL covariance row (dt subtracted separately as deterministic bias)
#   Row 2: rate stays constant
_F_BASE = np.array([
    [1.0, 0.0, -1.0],  # HI_t   = HI - rate * dt  (dt=1 here)
    [0.0, 1.0,  0.0],  # RUL covariance propagation (x[1] -= dt separately)
    [0.0, 0.0,  1.0],  # rate constant
], dtype=float)

# All 4 observations map primarily to HI (state[0])
# (RUL observation omitted — Cox/PINN provide it separately)
H = np.array([
    [1.0, 0.0, 0.0],   # rule_score  → HI
    [1.0, 0.0, 0.0],   # ml_score    → HI
    [1.0, 0.0, 0.0],   # survival_hi → HI
    [1.0, 0.0, 0.0],   # mahal_hi    → HI
], dtype=float)

# Process noise (Q per unit time): how much state drifts per day.
# Scaled by dt in update() so longer gaps accumulate more uncertainty.
q_per_day = 0.5 * np.eye(STATE_DIM, dtype=float)

# Observation noise (R): trust per sensor (variances in HI-score units)
# rule_score: σ=5 pts → var=25; ml_score: σ=5 → 25; survival: σ=6 → 36; mahal: σ=4 → 16
R = np.diag([25.0, 25.0, 36.0, 16.0]).astype(float)


class KalmanStateEstimator:
    """
    Linear Kalman Filter for health state estimation from multiple model outputs.

    State: x = [HI, RUL, degradation_rate]
    Observations: z = [rule_score, ml_score, survival_hi, mahal_hi]

    Missing observations (None or NaN) handled via masked updates.
    Variable time steps via dt parameter in update() and smooth_from_scores().

    Usage (typical per-request pattern — create fresh instance per inference call):
        est = KalmanStateEstimator()
        result = est.smooth_from_scores(history_with_dt)
        hi_smoothed = result['hi_kalman']

    Each entry in history should optionally carry a "dt" key (days, default=1.0).
    """

    def __init__(self, h_matrix=H, q_per_day=q_per_day, r_noise=R):
        self.H         = np.array(h_matrix,  dtype=float)
        self.q_per_day = np.array(q_per_day, dtype=float)
        self.R         = np.array(r_noise,   dtype=float)
        # State and covariance — initialized by reset()
        self.x: np.ndarray = np.zeros(STATE_DIM)
        self.P: np.ndarray = np.eye(STATE_DIM) * 100.0  # high initial uncertainty
        self._innovation_history: List[float] = []
        self._initialized: bool = False

    # ── Internal helpers ────────────────────────────────────────────────────────

    def _build_f(self, dt: float) -> np.ndarray:
        """
        Build time-varying transition matrix for elapsed dt (days).

        HI row:   HI_t = HI_{t-1} - rate * dt
        RUL row:  covariance propagation only; actual RUL -= dt applied post-multiply
        rate row: constant
        """
        return np.array([
            [1.0, 0.0, -dt],  # HI_t = HI - rate * dt
            [0.0, 1.0,  0.0], # RUL covariance (time-decay applied separately)
            [0.0, 0.0,  1.0], # rate constant
        ], dtype=float)

    def _obs_to_vector(self, obs: Dict) -> np.ndarray:
        """Convert observation dict to z vector (NaN for missing keys)."""
        return np.array([
            float(obs.get("rule_score",    np.nan)),
            float(obs.get("ml_score",      np.nan)),
            float(obs.get("survival_hi",   np.nan)),
            float(obs.get("mahal_hi",      np.nan)),
        ], dtype=float)

    # ── Public API ──────────────────────────────────────────────────────────────

    def reset(self, initial_hi: float = 80.0, initial_rul: float = 30.0) -> None:
        """Reset filter to initial state (call before first observation)."""
        self.x = np.array([initial_hi, initial_rul, 0.5], dtype=float)
        self.P = np.eye(STATE_DIM, dtype=float) * 100.0
        self._innovation_history = []
        self._initialized = True

    def update(self, obs: Dict, dt: float = 1.0) -> Dict:
        """
        Run one Kalman filter step with the given observations.

        Args:
            obs: Dict with zero or more of:
                 rule_score, ml_score, survival_hi, mahal_hi (all in [0, 100])
                 (The "dt" key is ignored here — pass dt explicitly.)
            dt:  Elapsed time since last update in days (default=1.0).
                 Use actual elapsed days from telemetry timestamps to avoid
                 RUL drain on burst requests or irregular sensor cadence.

        Returns:
            Dict with:
                hi_kalman (float, [0,100]),
                rul_kalman (float, days >= 0),
                degradation_rate (float),
                sensor_fault_flag (bool),
                innovation_norm (float),
                state_covariance_trace (float)
        """
        if not self._initialized:
            self.reset()

        dt = max(dt, 1e-6)  # guard against zero/negative dt

        # --- Predict step ---
        f_dt   = self._build_f(dt)
        x_pred = f_dt @ self.x
        x_pred[1] = max(0.0, x_pred[1] - dt)  # RUL decreases by elapsed time (deterministic)
        p_pred = f_dt @ self.P @ f_dt.T + self.q_per_day * dt  # noise scales with dt

        # --- Build observation vector, handle missing ---
        z_full     = self._obs_to_vector(obs)
        valid_mask = ~np.isnan(z_full)

        if not valid_mask.any():
            # No observations — just propagate prediction
            self.x = x_pred
            self.P = p_pred
            return {
                "hi_kalman":              float(np.clip(x_pred[0], 0, 100)),
                "rul_kalman":             float(max(0.0, x_pred[1])),
                "degradation_rate":       float(x_pred[2]),
                "sensor_fault_flag":      False,
                "innovation_norm":        0.0,
                "state_covariance_trace": float(np.trace(p_pred)),
            }

        # Mask to valid observations only
        h_valid = self.H[valid_mask]
        r_valid = self.R[np.ix_(valid_mask, valid_mask)]
        z_valid = z_full[valid_mask]

        # --- Update step ---
        S         = h_valid @ p_pred @ h_valid.T + r_valid  # innovation covariance
        K         = p_pred @ h_valid.T @ np.linalg.inv(S)   # Kalman gain
        innovation = z_valid - h_valid @ x_pred              # innovation vector
        self.x    = x_pred + K @ innovation
        self.P    = (np.eye(STATE_DIM) - K @ h_valid) @ p_pred

        # Clamp state to physical bounds
        self.x[0] = float(np.clip(self.x[0], 0.0, 100.0))
        self.x[1] = max(0.0, float(self.x[1]))
        self.x[2] = max(0.0, float(self.x[2]))

        # --- Innovation norm and fault detection ---
        innovation_norm = float(np.linalg.norm(innovation))
        self._innovation_history.append(innovation_norm)

        sensor_fault = False
        if len(self._innovation_history) >= 5:
            hist        = np.array(self._innovation_history)
            running_std = float(np.std(hist)) + 1e-9
            sensor_fault = innovation_norm > 3.0 * running_std

        return {
            "hi_kalman":              float(self.x[0]),
            "rul_kalman":             float(self.x[1]),
            "degradation_rate":       float(self.x[2]),
            "sensor_fault_flag":      bool(sensor_fault),
            "innovation_norm":        innovation_norm,
            "state_covariance_trace": float(np.trace(self.P)),
        }

    def smooth_from_scores(
        self,
        score_history: List[Dict],
        initial_hi: float = 80.0,
        initial_rul: float = 30.0,
    ) -> Dict:
        """
        Reset filter and replay a sequence of historical health observations.

        Each entry in score_history is an obs dict with zero or more of:
            rule_score, ml_score, survival_hi, mahal_hi
        and optionally:
            dt  (float, days since previous entry — default 1.0)

        Embedding actual elapsed days per entry is CRITICAL for correct RUL
        estimation when readings are non-uniform or burst-loaded.

        Returns the smoothed state after the final observation (same format as update()).
        """
        self.reset(initial_hi=initial_hi, initial_rul=initial_rul)
        result = {
            "hi_kalman":              initial_hi,
            "rul_kalman":             initial_rul,
            "degradation_rate":       0.5,
            "sensor_fault_flag":      False,
            "innovation_norm":        0.0,
            "state_covariance_trace": float(np.trace(self.P)),
        }
        for obs in score_history:
            dt     = float(obs.get("dt", 1.0))
            result = self.update(obs, dt=dt)
        return result

    def smooth(self, obs_sequence: List[Dict]) -> List[Dict]:
        """
        Run Kalman filter over a full sequence of observations.
        Returns list of state dicts, one per step.
        Each entry may include "dt" key (days, default=1.0).
        """
        self.reset()
        return [self.update(obs, dt=float(obs.get("dt", 1.0))) for obs in obs_sequence]

    @property
    def current_hi(self) -> float:
        return float(self.x[0])

    @property
    def current_rul(self) -> float:
        return float(max(0.0, self.x[1]))

    @property
    def innovation_history(self) -> List[float]:
        return list(self._innovation_history)


# ── Module-level singleton ──────────────────────────────────────────────────────

_kalman_estimator: Optional[KalmanStateEstimator] = None


def get_kalman_estimator() -> KalmanStateEstimator:
    """Return (or create) the module-level Kalman estimator singleton."""
    global _kalman_estimator
    if _kalman_estimator is None:
        _kalman_estimator = KalmanStateEstimator()
    return _kalman_estimator


def reset_kalman_estimator(initial_hi: float = 80.0, initial_rul: float = 30.0) -> None:
    """Reset the module-level singleton to fresh initial state."""
    get_kalman_estimator().reset(initial_hi=initial_hi, initial_rul=initial_rul)

