"""
Model D: Dempster-Shafer Evidence Theory Fusion Layer
Fuses outputs from Models A-C, E into a single unified health score.

Frame of discernment: Θ = {Healthy, Degrading, Critical, Unknown}

Each model output is converted to a Basic Probability Assignment (BPA) over Θ.
Dempster's combination rule is used when conflict K ≤ 0.8;
Yager's rule (conservative) is used when K > 0.8 to preserve Unknown mass.
"""
import logging
import numpy as np
from typing import Dict, List, Optional

from .core.config import config

logger = logging.getLogger(__name__)

# Frame labels
HEALTHY   = "Healthy"
DEGRADING = "Degrading"
CRITICAL  = "Critical"
UNKNOWN   = "Unknown"

FRAME = [HEALTHY, DEGRADING, CRITICAL, UNKNOWN]

# Conflict threshold: above this Yager's rule applies
CONFLICT_THRESHOLD = config.dst_conflict_threshold


def _model_output_to_bpa(output: Optional[Dict]) -> Dict[str, float]:
    """
    Convert a ModelOutput dict to a Basic Probability Assignment (BPA) over Θ.

    If output is None, all mass goes to Unknown (vacuous BPA — no evidence).

    Soft (continuous) BPA using piecewise-linear membership functions:
        m_H(hi)  = hi / 100                               — grows 0→1 as HI 0→100
        m_D(hi)  = 1 - |hi - 50| / 50                     — triangle, peak at HI=50
        m_C(hi)  = 1 - hi / 100                           — shrinks 1→0 as HI 0→100

    critical_prob scales the Critical membership; (1 - critical_prob) scales Healthy.
    All three raw masses are normalised to sum to 1 before applying confidence.
    Confidence controls how much mass bleeds into Unknown:
        m(Unknown) = 1 - confidence

    Replaces the original hard-threshold mapping that created discontinuous cliffs
    at HI=80 (H→D) and HI=50 (D→C) causing instability near boundaries.
    """
    if output is None:
        return {HEALTHY: 0.0, DEGRADING: 0.0, CRITICAL: 0.0, UNKNOWN: 1.0}

    hi         = float(output.get("health_index",  50.0))
    crit_prob  = float(output.get("critical_prob",  0.5))
    confidence = max(0.0, min(1.0, float(output.get("confidence", 0.5))))

    # Soft membership functions (continuous, no cliffs)
    h_raw = hi / 100.0                             # 0→1 as HI goes 0→100
    d_raw = max(0.0, 1.0 - abs(hi - 50.0) / 50.0) # triangle, peak=1 at HI=50
    c_raw = 1.0 - h_raw                            # 1→0 as HI goes 0→100

    # Blend critical membership with model's own critical_prob estimate
    c_scaled = c_raw * (0.5 + 0.5 * crit_prob)   # up-weight when model says critical
    h_scaled = h_raw * (1.0 - 0.5 * crit_prob)   # down-weight when model says critical
    d_scaled = d_raw                               # degrading unaffected by crit_prob

    raw_total = h_scaled + d_scaled + c_scaled
    if raw_total < 1e-9:
        raw_total = 1.0  # degenerate guard

    # Scale by confidence; remainder bleeds into Unknown
    bpa = {
        HEALTHY:   confidence * h_scaled / raw_total,
        DEGRADING: confidence * d_scaled / raw_total,
        CRITICAL:  confidence * c_scaled / raw_total,
        UNKNOWN:   1.0 - confidence,
    }

    # Normalise to exactly 1.0 (guard float rounding)
    total = sum(bpa.values())
    if total > 0:
        for k in FRAME:
            bpa[k] /= total

    return bpa


def _conflict_mass(m1: Dict[str, float], m2: Dict[str, float]) -> float:
    """Compute Dempster conflict factor K between two singleton-BPAs."""
    return sum(
        m1[l1] * m2[l2]
        for l1 in FRAME for l2 in FRAME
        if l1 != l2 and l1 != UNKNOWN and l2 != UNKNOWN
    )


def _intersect_label(label1: str, label2: str):
    """Return intersection label for two singleton/Unknown labels, or None if disjoint."""
    if label1 == UNKNOWN:
        return label2
    if label2 == UNKNOWN:
        return label1
    return label1 if label1 == label2 else None


def _normalise(bpa: Dict[str, float]) -> None:
    """Normalise BPA in-place so values sum to 1."""
    total = sum(bpa.values())
    if total > 0:
        for k in FRAME:
            bpa[k] /= total


def _dempster_combine(m1: Dict[str, float], m2: Dict[str, float]) -> tuple:
    """
    Combine two BPAs using Dempster's orthogonal sum.

    Returns (combined_bpa, K) where K = conflict factor in [0, 1].
    If K ≥ 1.0 (total conflict), falls back to vacuous BPA.
    """
    K = _conflict_mass(m1, m2)
    if K >= 1.0:
        logger.warning("Total conflict (K=1) in DST combination — returning vacuous BPA")
        return {HEALTHY: 0.0, DEGRADING: 0.0, CRITICAL: 0.0, UNKNOWN: 1.0}, float(K)

    denom = 1.0 - K
    combined = {}
    for target in FRAME:
        mass = sum(
            m1[l1] * m2[l2]
            for l1 in FRAME for l2 in FRAME
            if _intersect_label(l1, l2) == target
        )
        combined[target] = mass / denom if denom > 0 else 0.0

    _normalise(combined)
    return combined, float(K)


def _yager_combine(m1: Dict[str, float], m2: Dict[str, float]) -> tuple:
    """
    Yager's combination rule: conflict mass flows to Unknown (conservative).
    Used when K > CONFLICT_THRESHOLD.

    Returns (combined_bpa, K).
    """
    combined = dict.fromkeys(FRAME, 0.0)
    K = 0.0

    for label1 in FRAME:
        for label2 in FRAME:
            intersect = _intersect_label(label1, label2)
            product = m1[label1] * m2[label2]
            if intersect is None:
                K += product
            else:
                combined[intersect] += product

    combined[UNKNOWN] += K
    _normalise(combined)
    return combined, float(K)


def _combine_bpa_pair(m1: Dict[str, float], m2: Dict[str, float]) -> tuple:
    """Choose combination rule based on conflict level."""
    # First estimate K to decide rule
    conflict_mass = 0.0
    for label1 in FRAME:
        for label2 in FRAME:
            if label1 != label2 and label1 != UNKNOWN and label2 != UNKNOWN:
                conflict_mass += m1[label1] * m2[label2]

    if conflict_mass > CONFLICT_THRESHOLD:
        logger.warning(f"High conflict K={conflict_mass:.3f} > {CONFLICT_THRESHOLD} — using Yager's rule")
        return _yager_combine(m1, m2)
    else:
        return _dempster_combine(m1, m2)


def _combine_all_bpas(bpas: List[Dict[str, float]]) -> tuple:
    """
    Sequentially combine a list of BPAs, returning (combined_bpa, max_K).
    Returns vacuous BPA if list is empty.
    """
    if not bpas:
        return {HEALTHY: 0.0, DEGRADING: 0.0, CRITICAL: 0.0, UNKNOWN: 1.0}, 0.0

    combined = bpas[0]
    max_k = 0.0

    for m2 in bpas[1:]:
        combined, k = _combine_bpa_pair(combined, m2)
        max_k = max(max_k, k)

    return combined, max_k


def _bpa_to_score(bpa: Dict[str, float]) -> float:
    """
    Compute scalar health score from BPA.
    dst_score = Healthy*100 + Degrading*60 + Critical*10 + Unknown*50
    """
    return (
        bpa.get(HEALTHY,   0.0) * 100.0
        + bpa.get(DEGRADING, 0.0) * 60.0
        + bpa.get(CRITICAL,  0.0) * 10.0
        + bpa.get(UNKNOWN,   0.0) * 50.0
    )


def _bpa_to_verdict(bpa: Dict[str, float]) -> str:
    """Return the hypothesis with the highest mass (excluding Unknown unless dominant)."""
    # Find dominant hypothesis (highest mass)
    best = max(FRAME, key=lambda k: bpa.get(k, 0.0))
    return best


class DSTFusion:
    """
    Dempster-Shafer Evidence Theory fusion of multi-model health predictions.

    Usage:
        fusion = DSTFusion()
        result = fusion.fuse(model_outputs, kalman_state)
    """

    def fuse(
        self,
        model_outputs: List[Optional[Dict]],
        kalman_state: Optional[Dict] = None,
    ) -> Dict:
        """
        Fuse model outputs into a unified health score.

        Args:
            model_outputs: List of ModelOutput dicts (or None for vacuous).
                           Each has: model_id, health_index, critical_prob,
                           rul_estimate, uncertainty, confidence
            kalman_state:  Output of KalmanStateEstimator.update():
                           hi_kalman, rul_kalman, sensor_fault_flag, ...

        Returns:
            Dict with:
                unified_health_score  (float, [0, 100])
                dst_verdict           (str: Healthy|Degrading|Critical|Unknown)
                conflict_factor_K     (float, [0, 1])
                dst_score             (float, [0, 100])
                kalman_hi             (float, [0, 100])
                kalman_rul            (float, days)
                sensor_fault_flag     (bool)
                bpa_healthy           (float)
                bpa_degrading         (float)
                bpa_critical          (float)
                bpa_unknown           (float)
                model_disagreement_alert (bool)  — True if K > 0.8
        """
        # 1. Convert each model output to a BPA
        bpas = [_model_output_to_bpa(out) for out in model_outputs]

        # 2. Combine all BPAs
        combined_bpa, max_k = _combine_all_bpas(bpas)

        # 3. Compute DST score
        dst_score = _bpa_to_score(combined_bpa)

        # 4. Get Kalman smoothed HI
        kalman_hi  = 80.0  # default if no Kalman state
        kalman_rul = 30.0
        sensor_fault = False
        if kalman_state is not None:
            kalman_hi    = float(kalman_state.get("hi_kalman",  80.0))
            kalman_rul   = float(kalman_state.get("rul_kalman", 30.0))
            sensor_fault = bool(kalman_state.get("sensor_fault_flag", False))

        # 5. Blend DST + Kalman (70/30)
        unified = round(0.7 * dst_score + 0.3 * kalman_hi, 1)
        unified = float(max(0.0, min(100.0, unified)))

        # 6. DST verdict
        verdict = _bpa_to_verdict(combined_bpa)

        # 7. Log disagreement alert
        disagreement_alert = max_k > CONFLICT_THRESHOLD
        if disagreement_alert:
            logger.warning(
                f"model_disagreement_alert: conflict_factor_K={max_k:.3f} "
                f"— models disagree significantly"
            )

        return {
            "unified_health_score":   unified,
            "dst_verdict":            verdict,
            "conflict_factor_K":      round(float(max_k), 4),
            "dst_score":              round(float(dst_score), 1),
            "kalman_hi":              round(float(kalman_hi), 1),
            "kalman_rul":             round(float(kalman_rul), 1),
            "sensor_fault_flag":      sensor_fault,
            "bpa_healthy":            round(float(combined_bpa.get(HEALTHY,   0.0)), 4),
            "bpa_degrading":          round(float(combined_bpa.get(DEGRADING, 0.0)), 4),
            "bpa_critical":           round(float(combined_bpa.get(CRITICAL,  0.0)), 4),
            "bpa_unknown":            round(float(combined_bpa.get(UNKNOWN,   0.0)), 4),
            "model_disagreement_alert": disagreement_alert,
        }


# -----------------------------------------------------------------------
# Module-level singleton
# -----------------------------------------------------------------------

_dst_fusion: Optional[DSTFusion] = None


def get_dst_fusion() -> DSTFusion:
    """Return (or create) the module-level DST fusion singleton."""
    global _dst_fusion
    if _dst_fusion is None:
        _dst_fusion = DSTFusion()
    return _dst_fusion
