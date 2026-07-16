"""
Drift Detector
Statistical drift detection using Kolmogorov-Smirnov test + Population Stability Index.

Replaces simple Z-score threshold with proper two-sample KS test (accounts for sample
size, calibrated p-value). PSI tracks distributional shifts beyond mean (variance, skew).

Persistence: baseline statistics are saved to DRIFT_BASELINE_PATH (env var, default
/data/drift_baseline.json) so they survive service restarts.

KS test: H0 = reference and current drawn from same distribution.
         Reject (drift) when p_value < KS_P_THRESHOLD (default 0.05).

PSI thresholds:  < 0.1 = stable, 0.1–0.2 = slight shift, > 0.2 = significant drift.
"""
import json
import logging
import os
from collections import deque
from typing import Dict, List, Optional

import numpy as np
from scipy.stats import ks_2samp

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────
KS_P_THRESHOLD  = float(os.getenv("DRIFT_KS_P_THRESHOLD", "0.05"))
PSI_WARNING     = 0.10   # slight distribution shift
PSI_CRITICAL    = 0.20   # significant distribution shift (retrain trigger)
_BASELINE_PATH  = os.getenv(
    "DRIFT_BASELINE_PATH",
    os.path.join(os.path.dirname(__file__), "..", "drift_baseline.json"),
)

# Number of histogram bins for PSI calculation
_PSI_BINS = 10


# ── PSI helper ─────────────────────────────────────────────────────────────────

def _compute_psi(reference: np.ndarray, current: np.ndarray, bins: int = _PSI_BINS) -> float:
    """
    Population Stability Index for a single feature.

    PSI = Σ (P_cur - P_ref) * ln(P_cur / P_ref)

    Uses reference distribution to define bin edges.
    Clips fractions to [1e-4, 1] to avoid log(0).
    """
    # Determine bin edges from reference distribution
    _, bin_edges = np.histogram(reference, bins=bins)
    # Extend edges slightly to capture min/max of current
    bin_edges[0]  = min(bin_edges[0],  current.min()) - 1e-9
    bin_edges[-1] = max(bin_edges[-1], current.max()) + 1e-9

    ref_counts, _ = np.histogram(reference, bins=bin_edges)
    cur_counts, _ = np.histogram(current,   bins=bin_edges)

    ref_frac = np.clip(ref_counts / max(len(reference), 1), 1e-4, 1.0)
    cur_frac = np.clip(cur_counts / max(len(current),   1), 1e-4, 1.0)

    # Normalise so each sums to 1
    ref_frac /= ref_frac.sum()
    cur_frac /= cur_frac.sum()

    psi = float(np.sum((cur_frac - ref_frac) * np.log(cur_frac / ref_frac)))
    return round(max(0.0, psi), 6)


# ── Main class ─────────────────────────────────────────────────────────────────

class DriftDetector:
    """
    Detect data drift per feature using KS test + PSI.

    Baseline is persisted to disk so it survives restarts.
    """

    def __init__(self, window_size: int = 1000, feature_names: Optional[List[str]] = None):
        self.window_size   = window_size
        self.feature_names = feature_names or []
        self.baseline: deque = deque(maxlen=window_size)
        self.current:  deque = deque(maxlen=window_size)
        self._loaded_baseline: Optional[np.ndarray] = None  # persisted snapshot

        # Attempt to load persisted baseline on startup
        self._load_baseline()

    # ── Baseline persistence ────────────────────────────────────────────────────

    def _save_baseline(self) -> None:
        """Persist baseline statistics to JSON for survival across restarts."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(_BASELINE_PATH)), exist_ok=True)
            arr = np.array(self.baseline)
            payload = {
                "data":          arr.tolist(),
                "feature_names": self.feature_names,
                "n_samples":     len(arr),
            }
            with open(_BASELINE_PATH, "w", encoding="utf-8") as f:
                json.dump(payload, f)
            logger.info(
                f"DriftDetector: baseline saved ({len(arr)} samples) → {_BASELINE_PATH}"
            )
        except Exception as exc:
            logger.warning(f"DriftDetector: could not save baseline: {exc}")

    def _load_baseline(self) -> None:
        """Load persisted baseline from disk if available."""
        if not os.path.exists(_BASELINE_PATH):
            return
        try:
            with open(_BASELINE_PATH, "r", encoding="utf-8") as f:
                payload = json.load(f)
            data = payload.get("data", [])
            names = payload.get("feature_names", [])
            if data:
                arr = np.array(data)
                for row in arr:
                    self.baseline.append(row.tolist())
                self._loaded_baseline = arr
                if names and not self.feature_names:
                    self.feature_names = names
                logger.info(
                    f"DriftDetector: loaded persisted baseline "
                    f"({len(data)} samples) from {_BASELINE_PATH}"
                )
        except Exception as exc:
            logger.warning(f"DriftDetector: could not load baseline: {exc}")

    # ── Data ingestion ──────────────────────────────────────────────────────────

    def add_baseline(self, features: List[float]) -> None:
        """Add one observation to the reference (baseline) window."""
        self.baseline.append(features)
        if not self.feature_names:
            self.feature_names = [f"feature_{i}" for i in range(len(features))]
        self._update_stats()

    def add_current(self, features: List[float]) -> None:
        """Add one observation to the current (production) window."""
        self.current.append(features)

    def _update_stats(self) -> None:
        """Persist baseline when it crosses the minimum size threshold."""
        if len(self.baseline) >= 100 and len(self.baseline) % 100 == 0:
            self._save_baseline()

    # ── Detection ───────────────────────────────────────────────────────────────

    def detect_drift(self) -> Dict:
        """
        Run per-feature KS test and PSI on baseline vs current window.

        Returns:
            drift_detected (bool)
            feature_scores (list of per-feature results)
            avg_psi (float)
            baseline_count / current_count (int)
        """
        if len(self.baseline) < 100 or len(self.current) < 100:
            return {
                "drift_detected":  False,
                "reason":          "insufficient_data",
                "baseline_count":  len(self.baseline),
                "current_count":   len(self.current),
            }

        baseline_arr = np.array(self.baseline)
        current_arr  = np.array(self.current)
        n_features   = baseline_arr.shape[1]

        feature_scores = []
        any_drift = False

        for i in range(n_features):
            ref_col = baseline_arr[:, i]
            cur_col = current_arr[:, i]
            name    = self.feature_names[i] if i < len(self.feature_names) else f"feature_{i}"

            # KS test — proper two-sample statistical test
            ks_stat, p_value = ks_2samp(ref_col, cur_col)
            ks_drift = bool(p_value < KS_P_THRESHOLD)

            # PSI — catches distributional shifts beyond mean
            psi = _compute_psi(ref_col, cur_col)
            # KS test is statistically calibrated (p-value accounts for sample size).
            # PSI is informational only: unreliable at n<500 due to sampling variance.
            feature_drift = ks_drift
            if feature_drift:
                any_drift = True

            if psi > PSI_CRITICAL:
                psi_level = "critical"
            elif psi > PSI_WARNING:
                psi_level = "warning"
            else:
                psi_level = "stable"
            feature_scores.append({
                "feature":       name,
                "feature_index": i,
                "ks_statistic":  round(float(ks_stat),  6),
                "p_value":       round(float(p_value),  6),
                "ks_drift":      ks_drift,
                "psi":           psi,
                "psi_level":     psi_level,
                "drift":         feature_drift,
            })

        avg_psi = float(np.mean([s["psi"] for s in feature_scores]))

        if any_drift:
            drifted = [s["feature"] for s in feature_scores if s["drift"]]
            logger.warning(
                f"DriftDetector: drift detected on features {drifted}. "
                f"avg_PSI={avg_psi:.4f}"
            )

        return {
            "drift_detected":  any_drift,
            "avg_psi":         round(avg_psi, 4),
            "feature_scores":  feature_scores,
            "baseline_count":  len(self.baseline),
            "current_count":   len(self.current),
            "ks_threshold":    KS_P_THRESHOLD,
            "psi_warning":     PSI_WARNING,
            "psi_critical":    PSI_CRITICAL,
        }

    def get_status(self) -> Dict:
        """Return detector status including baseline health."""
        return {
            "baseline_count":  len(self.baseline),
            "current_count":   len(self.current),
            "has_baseline":    len(self.baseline) >= 100,
            "persisted":       os.path.exists(_BASELINE_PATH),
            "feature_names":   self.feature_names,
        }

    def reset_current(self) -> None:
        """Clear current window (call after addressing detected drift)."""
        self.current.clear()

    def reset_baseline(self) -> None:
        """Replace baseline with current window (adapt to new distribution)."""
        if len(self.current) >= 100:
            self.baseline.clear()
            for obs in self.current:
                self.baseline.append(obs)
            self.current.clear()
            self._save_baseline()
            logger.info("DriftDetector: baseline reset to current distribution")


# ── Module-level singleton ─────────────────────────────────────────────────────

FEATURE_NAMES_DEFAULT = [
    "air_temperature", "process_temperature",
    "rotational_speed", "torque", "tool_wear",
]

drift_detector = DriftDetector(feature_names=FEATURE_NAMES_DEFAULT)


def check_drift(features: List[float]) -> Dict:
    """Add features to current window and return drift detection result."""
    drift_detector.add_current(features)
    return drift_detector.detect_drift()


def update_baseline(features: List[float]) -> None:
    """Add features to reference baseline."""
    drift_detector.add_baseline(features)


def get_drift_status() -> Dict:
    """Return drift detector status."""
    return drift_detector.get_status()
