"""
Model E: Isolation Forest + CUSUM Control Chart Anomaly Ensemble
Dual-gate: BOTH detectors must fire to flag anomaly (reduces false alarms).

IsolationForest: multivariate outlier detection
  - contamination=0.05, n_estimators=200
  - threshold on decision_function score: < -0.65 = anomaly
  - (NOT the contamination param — that's training-time; threshold is inference-time)

CUSUM: per-sensor drift detection
  - S⁺_t = max(0, S⁺_{t-1} + (x_t - μ₀ - k))
  - S⁻_t = max(0, S⁻_{t-1} - (x_t - μ₀ + k))
  - alarm when S⁺_t > h or S⁻_t > h
  - k = 0.5σ (allowance), h = 5σ (decision threshold)

Reconciliation: anomaly_detected = iso_anomaly AND any(cusum_alarms)
"""
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    "air_temperature", "process_temperature",
    "rotational_speed", "torque", "tool_wear",
]
ISO_SCORE_THRESHOLD = -0.65   # decision_function below this = anomaly


# -----------------------------------------------------------------------
# CUSUM Detector (single-sensor)
# -----------------------------------------------------------------------

class CUSUMDetector:
    """
    Cumulative Sum (CUSUM) control chart for single-sensor drift detection.

    Detects sustained shifts of magnitude > k*sigma within h/sigma steps.

    Usage:
        detector = CUSUMDetector(k=0.5*sigma, h=5*sigma)
        for x in stream:
            if detector.update(x, baseline_mean):
                print("Drift alarm!")
        detector.reset()  # reset after alarm
    """

    def __init__(self, k: float, h: float):
        """
        Args:
            k: Allowance parameter (slack). Typically 0.5 * target_shift_sigma.
            h: Decision threshold. Typically 4-5 * sigma.
        """
        self.k = float(k)
        self.h = float(h)
        self.s_pos: float = 0.0   # upper CUSUM statistic
        self.s_neg: float = 0.0   # lower CUSUM statistic
        self.n_updates: int = 0

    def update(self, x_t: float, mu_0: float) -> bool:
        """
        Update CUSUM statistics with new observation.

        Standard two-sided CUSUM formulas:
          S⁺_t = max(0, S⁺_{t-1} + (x_t - μ₀ - k))   ← detects upward drift
          S⁻_t = max(0, S⁻_{t-1} - (x_t - μ₀ + k))   ← detects downward drift

        Args:
            x_t: New observation
            mu_0: In-control (baseline) mean

        Returns:
            True if alarm triggered (shift detected), False otherwise
        """
        self.s_pos = max(0.0, self.s_pos + (x_t - mu_0 - self.k))
        self.s_neg = max(0.0, self.s_neg - (x_t - mu_0 + self.k))
        self.n_updates += 1
        return self.s_pos > self.h or self.s_neg > self.h

    def reset(self) -> None:
        """Reset statistics to zero (e.g., after alarm investigation)."""
        self.s_pos = 0.0
        self.s_neg = 0.0

    @property
    def is_alarmed(self) -> bool:
        return self.s_pos > self.h or self.s_neg > self.h


# -----------------------------------------------------------------------
# Anomaly Ensemble
# -----------------------------------------------------------------------

class AnomalyEnsemble:
    """
    Dual-gate anomaly detector combining Isolation Forest and CUSUM charts.

    fit() on healthy baseline data → predict_with_history() for new observations.

    Thread-safety: The IsolationForest is read-only after fit(). The legacy
    predict() and replay_history() methods mutate self._cusums and are NOT
    safe under concurrent requests — use predict_with_history() instead,
    which creates fresh CUSUM detectors per call.
    """

    def __init__(
        self,
        contamination: float = 0.05,
        n_estimators: int = 200,
        iso_threshold: float = ISO_SCORE_THRESHOLD,
    ):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.iso_threshold = iso_threshold
        self._iso_forest: Optional[IsolationForest] = None
        self._cusums: Dict[str, CUSUMDetector] = {}
        self._baselines: Dict[str, Tuple[float, float]] = {}  # {name: (mu, sigma)}
        self._fitted = False
        self._iso_scores_sorted: Optional[np.ndarray] = None

    def fit(self, X: np.ndarray, feature_names: List[str] = None) -> "AnomalyEnsemble":
        """
        Fit the ensemble on healthy (in-control) data.

        Args:
            X: (n_samples, n_features) array of healthy sensor readings
            feature_names: Names for each column (default: FEATURE_NAMES[:n_cols])

        Returns:
            self
        """
        if feature_names is None:
            feature_names = FEATURE_NAMES[:X.shape[1]]
        X = np.asarray(X, dtype=float)

        # Fit Isolation Forest
        self._iso_forest = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=42,
        )
        self._iso_forest.fit(X)

        # Compute per-feature baselines (mu, sigma) for CUSUM
        self._cusums = {}
        self._baselines = {}
        for i, name in enumerate(feature_names):
            col = X[:, i]
            mu = float(col.mean())
            sigma = float(col.std()) + 1e-9
            self._baselines[name] = (mu, sigma)
            k = 0.5 * sigma
            h = 5.0 * sigma
            self._cusums[name] = CUSUMDetector(k=k, h=h)

        # Store decision_function scores on training data → empirical CDF
        iso_scores = self._iso_forest.decision_function(X)
        self._iso_scores_sorted = np.sort(iso_scores)
        self._fitted = True
        logger.info(
            f"AnomalyEnsemble fitted on {len(X)} samples, "
            f"{len(feature_names)} features"
        )
        return self

    def predict_with_history(
        self,
        x: np.ndarray,
        feature_names: List[str] = None,
        history: List[np.ndarray] = None,
    ) -> Dict:
        """
        Stateless anomaly prediction — safe for concurrent requests.

        Creates fresh CUSUM detectors per call (not stored on self), replays
        the provided history through them, then scores the latest observation x.
        The global IsolationForest singleton is read-only and always safe.

        Args:
            x: array-like (n_features,) — the latest sensor reading to score
            feature_names: Names for each feature (default: FEATURE_NAMES[:n])
            history: Optional list of prior observations (oldest first), each
                     of shape (n_features,). Used to warm-start CUSUM state.
                     Pass logs[:-1] from the caller — do NOT include x itself.

        Returns:
            ModelOutput dict (same schema as predict()):
                model_id, health_index (0-100), critical_prob (0-1),
                rul_estimate (None), uncertainty, confidence,
                is_anomaly (bool), iso_score (float), cusum_alarms (dict)
        """
        if not self._fitted:
            return {
                "model_id":      "model_e_anomaly",
                "health_index":  50.0,
                "critical_prob": 0.5,
                "rul_estimate":  None,
                "uncertainty":   0.5,
                "confidence":    0.0,
                "is_anomaly":    False,
                "iso_score":     0.0,
                "cusum_alarms":  {},
            }

        x = np.asarray(x, dtype=float)
        if feature_names is None:
            feature_names = list(self._baselines.keys())

        # --- Build fresh per-request CUSUM detectors (no shared mutable state) ---
        temp_cusums: Dict[str, CUSUMDetector] = {}
        for name, (mu, sigma) in self._baselines.items():
            temp_cusums[name] = CUSUMDetector(k=0.5 * sigma, h=5.0 * sigma)

        # --- Warm-start: replay history through fresh detectors ---
        if history:
            for obs in history:
                obs_arr = np.asarray(obs, dtype=float)
                for i, name in enumerate(feature_names):
                    if name not in temp_cusums or i >= len(obs_arr):
                        continue
                    mu = self._baselines[name][0]
                    temp_cusums[name].update(float(obs_arr[i]), mu)

        # --- Isolation Forest gate (read-only, always thread-safe) ---
        iso_score = float(self._iso_forest.decision_function(x.reshape(1, -1))[0])
        iso_anomaly = iso_score < self.iso_threshold

        # --- CUSUM gate using fresh per-request detectors ---
        cusum_alarms: Dict[str, bool] = {}
        for i, name in enumerate(feature_names):
            if name in temp_cusums and i < len(x):
                mu = self._baselines[name][0]
                alarmed = temp_cusums[name].update(float(x[i]), mu)
                cusum_alarms[name] = alarmed
        any_cusum_alarm = any(cusum_alarms.values())

        # --- Dual-gate reconciliation ---
        anomaly_detected = iso_anomaly and any_cusum_alarm

        # --- Health Index from Isolation Forest score ---
        pct_rank = float(np.searchsorted(self._iso_scores_sorted, iso_score)) / max(1, len(self._iso_scores_sorted))
        hi = round(100.0 * pct_rank, 2)
        hi = max(0.0, min(100.0, hi))
        critical_prob = 1.0 - (hi / 100.0)

        if anomaly_detected:
            hi = min(hi, 20.0)
            critical_prob = max(critical_prob, 0.8)

        return {
            "model_id":      "model_e_anomaly",
            "health_index":  hi,
            "critical_prob": float(critical_prob),
            "rul_estimate":  None,
            "uncertainty":   float(abs(iso_score)),
            "confidence":    0.85 if self._fitted else 0.0,
            "is_anomaly":    bool(anomaly_detected),
            "iso_score":     iso_score,
            "cusum_alarms":  cusum_alarms,
        }

    def predict(
        self, x: np.ndarray, feature_names: List[str] = None
    ) -> Dict:
        """
        Predict anomaly status for a single observation.

        WARNING: This method mutates self._cusums and is NOT safe under
        concurrent requests. Use predict_with_history() for production inference.

        Args:
            x: array-like (n_features,) — single sensor reading
            feature_names: Names for each feature (default: FEATURE_NAMES[:n])

        Returns:
            ModelOutput dict:
                model_id, health_index (0-100), critical_prob (0-1),
                rul_estimate (None), uncertainty, confidence,
                is_anomaly (bool), iso_score (float), cusum_alarms (dict)
        """
        if not self._fitted:
            # Unfitted — return neutral result
            return {
                "model_id":      "model_e_anomaly",
                "health_index":  50.0,
                "critical_prob": 0.5,
                "rul_estimate":  None,
                "uncertainty":   0.5,
                "confidence":    0.0,
                "is_anomaly":    False,
                "iso_score":     0.0,
                "cusum_alarms":  {},
            }

        x = np.asarray(x, dtype=float)
        if feature_names is None:
            feature_names = list(self._baselines.keys())

        # --- Isolation Forest gate ---
        iso_score = float(self._iso_forest.decision_function(x.reshape(1, -1))[0])
        iso_anomaly = iso_score < self.iso_threshold

        # --- CUSUM gate (per-feature) ---
        cusum_alarms: Dict[str, bool] = {}
        for i, name in enumerate(feature_names):
            if name in self._cusums and i < len(x):
                mu = self._baselines[name][0]
                alarmed = self._cusums[name].update(float(x[i]), mu)
                cusum_alarms[name] = alarmed
        any_cusum_alarm = any(cusum_alarms.values())

        # --- Dual-gate reconciliation ---
        # BOTH must trigger for anomaly to be flagged
        anomaly_detected = iso_anomaly and any_cusum_alarm

        # --- Health Index from Isolation Forest score ---
        # Map iso_score to percentile rank → [0, 100]
        # Higher score = more normal = higher HI
        pct_rank = float(np.searchsorted(self._iso_scores_sorted, iso_score)) / max(1, len(self._iso_scores_sorted))
        hi = round(100.0 * pct_rank, 2)  # high iso_score rank → high HI
        hi = max(0.0, min(100.0, hi))
        critical_prob = 1.0 - (hi / 100.0)

        if anomaly_detected:
            hi = min(hi, 20.0)  # Hard cap at 20 when anomaly confirmed
            critical_prob = max(critical_prob, 0.8)

        return {
            "model_id":      "model_e_anomaly",
            "health_index":  hi,
            "critical_prob": float(critical_prob),
            "rul_estimate":  None,
            "uncertainty":   float(abs(iso_score)),
            "confidence":    0.85 if self._fitted else 0.0,
            "is_anomaly":    bool(anomaly_detected),
            "iso_score":     iso_score,
            "cusum_alarms":  cusum_alarms,
        }

    def replay_history(
        self,
        history: List[np.ndarray],
        feature_names: List[str] = None,
    ) -> None:
        """
        Warm-start CUSUM state by replaying historical observations (excluding latest).

        WARNING: Mutates self._cusums — NOT safe under concurrent requests.
        Use predict_with_history(history=...) instead.

        Args:
            history: List of 1-D arrays, each of shape (n_features,), oldest first.
                     Should be all entries EXCEPT the last one.
            feature_names: Column names matching the order of each array.
                           Defaults to self._baselines keys in insertion order.
        """
        if not self._fitted or len(history) == 0:
            return

        names = feature_names or list(self._baselines.keys())
        # Reset CUSUM stats before replay
        for det in self._cusums.values():
            det.reset()

        for obs in history:
            obs_arr = np.asarray(obs, dtype=float)
            for i, name in enumerate(names):
                if name not in self._cusums or i >= len(obs_arr):
                    continue
                mu, _ = self._baselines[name]
                self._cusums[name].update(float(obs_arr[i]), mu)

    def reset_cusum(self, feature_name: Optional[str] = None) -> None:
        """Reset CUSUM detector(s) after alarm investigation."""
        if feature_name:
            if feature_name in self._cusums:
                self._cusums[feature_name].reset()
        else:
            for det in self._cusums.values():
                det.reset()

    @property
    def is_fitted(self) -> bool:
        return self._fitted


# -----------------------------------------------------------------------
# Module-level singleton
# -----------------------------------------------------------------------

_anomaly_ensemble: Optional[AnomalyEnsemble] = None


def get_anomaly_ensemble() -> Optional[AnomalyEnsemble]:
    return _anomaly_ensemble


def fit_anomaly_ensemble(
    X: np.ndarray,
    feature_names: List[str] = None,
) -> AnomalyEnsemble:
    """Fit (or refit) the module-level ensemble singleton."""
    global _anomaly_ensemble
    _anomaly_ensemble = AnomalyEnsemble()
    _anomaly_ensemble.fit(X, feature_names)
    return _anomaly_ensemble

