"""
Model F: Linear Kalman Filter State Estimator
Smooths health state [HI, RUL, degradation_rate] from noisy multi-model observations.
Treats each model output as a noisy measurement, automatically weighted by noise covariance.
Supports missing observations (NaN masking).
"""
import logging
import numpy as np
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# State dimension: [HI, RUL, degradation_rate]
STATE_DIM = 3
# Observation dimension: [rule_score, ml_score, survival_hi, mahal_hi]
OBS_DIM = 4

# Transition matrix: HI_t = HI_{t-1} - rate, RUL_t = RUL_{t-1} - 1, rate stays
F = np.array([
    [1.0, -1.0, 0.0],   # HI_{t} = HI_{t-1} - RUL_delta*rate (simplified: -rate*1)
    [0.0,  1.0, -1.0],  # RUL_{t} = RUL_{t-1} - 1
    [0.0,  0.0,  1.0],  # rate stays constant
], dtype=float)

# All 4 observations map primarily to HI (state[0])
# (We ignore RUL observation for simplicity — Cox/PINN provide it separately)
H = np.array([
    [1.0, 0.0, 0.0],   # rule_score → HI
    [1.0, 0.0, 0.0],   # ml_score → HI
    [1.0, 0.0, 0.0],   # survival_hi → HI
    [1.0, 0.0, 0.0],   # mahal_hi → HI
], dtype=float)

# Process noise (Q): how much state can drift per step
Q = 0.5 * np.eye(STATE_DIM, dtype=float)

# Observation noise (R): how much we trust each sensor (variances)
# rule_score: σ=5 pts → var=25; ml_score: σ=5 → 25; survival: σ=6 → 36; mahal: σ=4 → 16
R = np.diag([25.0, 25.0, 36.0, 16.0]).astype(float)


class KalmanStateEstimator:
    """
    Linear Kalman Filter for health state estimation from multiple model outputs.

    State: x = [HI, RUL, degradation_rate]
    Observations: z = [rule_score, ml_score, survival_hi, mahal_hi]

    Missing observations (None or NaN) are handled via masked updates.

    Usage:
        est = KalmanStateEstimator()
        est.reset()
        for step in time_series:
            result = est.update(obs_dict)
            hi_smoothed = result['hi_kalman']
    """

    def __init__(self, F=F, H=H, Q=Q, R=R):
        self.F = np.array(F, dtype=float)
        self.H = np.array(H, dtype=float)
        self.Q = np.array(Q, dtype=float)
        self.R = np.array(R, dtype=float)
        # State and covariance — initialized by reset()
        self.x: np.ndarray = np.zeros(STATE_DIM)
        self.P: np.ndarray = np.eye(STATE_DIM) * 100.0  # high initial uncertainty
        self._innovation_history: List[float] = []
        self._initialized: bool = False

    def reset(self, initial_hi: float = 80.0, initial_rul: float = 30.0) -> None:
        """Reset filter to initial state (call before first observation)."""
        self.x = np.array([initial_hi, initial_rul, 0.5], dtype=float)
        self.P = np.eye(STATE_DIM, dtype=float) * 100.0
        self._innovation_history = []
        self._initialized = True

    def _obs_to_vector(self, obs: Dict) -> np.ndarray:
        """Convert observation dict to z vector (NaN for missing keys)."""
        return np.array([
            float(obs.get("rule_score",    np.nan)),
            float(obs.get("ml_score",      np.nan)),
            float(obs.get("survival_hi",   np.nan)),
            float(obs.get("mahal_hi",      np.nan)),
        ], dtype=float)

    def update(self, obs: Dict) -> Dict:
        """
        Run one Kalman filter step with the given observations.

        Args:
            obs: Dict with zero or more of:
                 rule_score, ml_score, survival_hi, mahal_hi (all in [0, 100])

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

        # --- Predict step ---
        x_pred = self.F @ self.x
        P_pred = self.F @ self.P @ self.F.T + self.Q

        # --- Build observation vector, handle missing ---
        z_full = self._obs_to_vector(obs)
        valid_mask = ~np.isnan(z_full)

        if not valid_mask.any():
            # No observations — just propagate prediction
            self.x = x_pred
            self.P = P_pred
            return {
                "hi_kalman":              float(np.clip(x_pred[0], 0, 100)),
                "rul_kalman":             float(max(0.0, x_pred[1])),
                "degradation_rate":       float(x_pred[2]),
                "sensor_fault_flag":      False,
                "innovation_norm":        0.0,
                "state_covariance_trace": float(np.trace(P_pred)),
            }

        # Mask to valid observations only
        H_valid = self.H[valid_mask]      # (n_valid, STATE_DIM)
        R_valid = self.R[np.ix_(valid_mask, valid_mask)]  # (n_valid, n_valid)
        z_valid = z_full[valid_mask]       # (n_valid,)

        # --- Update step ---
        S = H_valid @ P_pred @ H_valid.T + R_valid          # innovation covariance
        K = P_pred @ H_valid.T @ np.linalg.inv(S)           # Kalman gain
        innovation = z_valid - H_valid @ x_pred              # innovation vector
        self.x = x_pred + K @ innovation
        self.P = (np.eye(STATE_DIM) - K @ H_valid) @ P_pred

        self.x[0] = float(np.clip(self.x[0], 0.0, 100.0))
        self.x[1] = max(0.0, float(self.x[1]))
        self.x[2] = max(0.0, float(self.x[2]))

        # --- Innovation norm and fault detection ---
        innovation_norm = float(np.linalg.norm(innovation))
        self._innovation_history.append(innovation_norm)

        # Sensor fault: norm > 3 * running std of innovations
        if len(self._innovation_history) >= 5:
            hist = np.array(self._innovation_history)
            running_std = float(np.std(hist)) + 1e-9
            sensor_fault = innovation_norm > 3.0 * running_std
        else:
            sensor_fault = False   # not enough history to judge

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
        Reset filter and run through a sequence of historical health observations.

        Each entry in score_history is an obs dict with zero or more of:
            rule_score, ml_score, survival_hi, mahal_hi

        Returns the smoothed state after the final observation — same format
        as update().

        Args:
            score_history: List of obs dicts, oldest first.
            initial_hi: Initial health index assumption (default 80).
            initial_rul: Initial RUL assumption in days (default 30).
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
            result = self.update(obs)
        return result

    def smooth(self, obs_sequence: List[Dict]) -> List[Dict]:
        """
        Run Kalman filter over a full sequence of observations.
        Returns list of state dicts, one per step.
        """
        self.reset()
        return [self.update(obs) for obs in obs_sequence]

    @property
    def current_hi(self) -> float:
        return float(self.x[0])

    @property
    def current_rul(self) -> float:
        return float(max(0.0, self.x[1]))

    @property
    def innovation_history(self) -> List[float]:
        return list(self._innovation_history)


# -----------------------------------------------------------------------
# Module-level singleton
# -----------------------------------------------------------------------

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
