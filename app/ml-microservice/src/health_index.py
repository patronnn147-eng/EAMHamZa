"""
Model C: Mahalanobis Distance Health Index
Uses GMM on healthy-state data to establish a baseline, then measures
how far each new observation is from that baseline using Mahalanobis distance.
HI = 100 * (1 - percentile_rank(D_M²)) → 100 = perfectly healthy, 0 = extreme anomaly
"""
import numpy as np
import logging
from typing import Dict, List, Optional
from sklearn.mixture import GaussianMixture

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    "air_temperature", "process_temperature",
    "rotational_speed", "torque", "tool_wear"
]


class MahalanobisHealthIndex:
    """
    Mahalanobis distance-based Health Index using GMM baseline.

    fit() on healthy-state sensor data → score() for new observations.
    Thread-safe for read-only scoring after fit.
    """

    def __init__(self, n_components: int = 3, reg_covar: float = 1e-6):
        self.n_components = n_components
        self.reg_covar = reg_covar
        self._fitted = False
        # Populated by fit()
        self.mu: Optional[np.ndarray] = None
        self.sigma_inv: Optional[np.ndarray] = None
        self._dm2_sorted: Optional[np.ndarray] = None  # sorted D_M² values for CDF
        self._dm2_mean: float = 0.0
        self._dm2_std: float = 1.0
        self._anomaly_threshold: float = float("inf")

    def fit(self, healthy_snapshots: np.ndarray) -> "MahalanobisHealthIndex":
        """
        Fit GMM on healthy sensor data and store Mahalanobis distance baseline.

        Args:
            healthy_snapshots: np.ndarray of shape (n_samples, 5)
                               columns: [air_temp, process_temp, rpm, torque, tool_wear]

        Returns:
            self (for chaining)
        """
        if len(healthy_snapshots) < 10:
            raise ValueError(
                f"Need at least 10 healthy samples to fit, got {len(healthy_snapshots)}"
            )
        X = np.asarray(healthy_snapshots, dtype=float)
        n_comp = min(self.n_components, len(X) // 5)  # cap components to data size

        gmm = GaussianMixture(
            n_components=n_comp,
            covariance_type="full",
            reg_covar=self.reg_covar,
            random_state=42,
            max_iter=200,
        )
        gmm.fit(X)

        # Use dominant component (highest weight) as healthy centroid
        dominant_idx = int(np.argmax(gmm.weights_))
        self.mu = gmm.means_[dominant_idx]
        sigma = gmm.covariances_[dominant_idx]

        # Regularize and invert covariance
        sigma_reg = sigma + self.reg_covar * np.eye(sigma.shape[0])
        try:
            self.sigma_inv = np.linalg.inv(sigma_reg)
        except np.linalg.LinAlgError:
            logger.warning("Covariance inversion failed, using pseudo-inverse")
            self.sigma_inv = np.linalg.pinv(sigma_reg)

        # Compute D_M² for all training points → empirical CDF
        dm2_train = self._compute_dm2_batch(X)
        self._dm2_sorted = np.sort(dm2_train)
        self._dm2_mean = float(np.mean(dm2_train))
        self._dm2_std = float(np.std(dm2_train)) + 1e-9
        # 3-sigma anomaly threshold (Chebyshev-compatible)
        self._anomaly_threshold = self._dm2_mean + 3.0 * self._dm2_std
        self._fitted = True
        logger.info(
            f"MahalanobisHealthIndex fitted on {len(X)} samples. "
            f"Threshold D_M²={self._anomaly_threshold:.2f}"
        )
        return self

    def _compute_dm2(self, x: np.ndarray) -> float:
        """Compute Mahalanobis distance squared for a single sample."""
        diff = x - self.mu
        return float(diff @ self.sigma_inv @ diff)

    def _compute_dm2_batch(self, X: np.ndarray) -> np.ndarray:
        """Compute D_M² for all rows in X."""
        diff = X - self.mu  # (n, d)
        # (n, d) @ (d, d) @ (d, n) → take diagonal
        return np.einsum("ni,ij,nj->n", diff, self.sigma_inv, diff)

    def _percentile_rank(self, dm2: float) -> float:
        """
        Compute percentile rank of dm2 in training distribution via empirical CDF.
        Returns value in [0, 1]: 0 = lowest (most healthy), 1 = highest (most anomalous).
        """
        idx = np.searchsorted(self._dm2_sorted, dm2, side="right")
        return float(idx) / float(len(self._dm2_sorted))

    def score(self, x) -> Dict:
        """
        Compute Health Index for a single observation.

        Args:
            x: array-like of shape (5,) — [air_temp, process_temp, rpm, torque, tool_wear]
               OR a FeatureSnapshot dict (extracts first 5 sensor values)

        Returns:
            ModelOutput dict:
                model_id, health_index (0-100), critical_prob (0-1),
                rul_estimate (None), uncertainty, confidence,
                is_anomaly (bool), dm2 (float), percentile_rank (float)
        """
        if not self._fitted:
            raise RuntimeError("Call fit() before score()")

        if isinstance(x, dict):
            x = np.array([
                x.get("air_temperature", 298),
                x.get("process_temperature", 308),
                x.get("rotational_speed", 1500),
                x.get("torque", 40),
                x.get("tool_wear", 0),
            ], dtype=float)
        else:
            x = np.asarray(x, dtype=float)

        dm2 = self._compute_dm2(x)
        pct_rank = self._percentile_rank(dm2)
        hi = round(float(100.0 * (1.0 - pct_rank)), 2)
        hi = max(0.0, min(100.0, hi))
        is_anomaly = dm2 > self._anomaly_threshold

        # Confidence: high when fit had many samples
        confidence = min(0.95, 0.6 + 0.35 * min(1.0, len(self._dm2_sorted) / 500))

        return {
            "model_id":      "model_c_mahal_hi",
            "health_index":  hi,
            "critical_prob": float(pct_rank),
            "rul_estimate":  None,
            "uncertainty":   float(self._dm2_std / (self._dm2_mean + 1e-9)),
            "confidence":    confidence,
            "is_anomaly":    bool(is_anomaly),
            "dm2":           float(dm2),
            "percentile_rank": float(pct_rank),
        }

    def score_batch(self, X: np.ndarray) -> List[Dict]:
        """Score multiple observations."""
        return [self.score(row) for row in X]

    @property
    def is_fitted(self) -> bool:
        return self._fitted


# Module-level singleton — loaded lazily and refitted when healthy data arrives
_health_index_model: Optional[MahalanobisHealthIndex] = None


def get_health_index_model() -> Optional[MahalanobisHealthIndex]:
    """Return the module-level singleton, None if not yet fitted."""
    return _health_index_model


def fit_health_index(healthy_snapshots: np.ndarray) -> MahalanobisHealthIndex:
    """Fit (or refit) the module-level singleton and return it."""
    global _health_index_model
    _health_index_model = MahalanobisHealthIndex()
    _health_index_model.fit(healthy_snapshots)
    return _health_index_model
