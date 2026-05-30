"""
DST consistency test: conflict factor K < 0.8 under normal conditions.
Also asserts dst_verdict == 'Healthy' for clearly healthy telemetry.
Fails until Wave 2 (dst_fusion.py) is implemented.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../app/ml-microservice/src'))

import pytest

HEALTHY_MODEL_OUTPUTS = [
    {"model_id": "model_c_hi",      "health_index": 88.0, "critical_prob": 0.05, "rul_estimate": 45.0, "uncertainty": 1.5, "confidence": 0.9},
    {"model_id": "model_b_survival","health_index": 85.0, "critical_prob": 0.08, "rul_estimate": 40.0, "uncertainty": 3.0, "confidence": 0.85},
    {"model_id": "model_e_anomaly", "health_index": 90.0, "critical_prob": 0.03, "rul_estimate": None, "uncertainty": 0.5, "confidence": 0.92},
]
HEALTHY_KALMAN = {"hi_kalman": 87.0, "rul_kalman": 42.0, "sensor_fault_flag": False}

def test_dst_normal_conditions_low_conflict():
    """Under normal healthy conditions, DST conflict K must be < 0.8."""
    from dst_fusion import DSTFusion
    fusion = DSTFusion()
    result = fusion.fuse(HEALTHY_MODEL_OUTPUTS, HEALTHY_KALMAN)
    K = result["conflict_factor_K"]
    assert K < 0.8, f"Conflict K={K:.3f} is too high for healthy machine"

def test_dst_healthy_verdict():
    """Clearly healthy telemetry must produce Healthy verdict."""
    from dst_fusion import DSTFusion
    fusion = DSTFusion()
    result = fusion.fuse(HEALTHY_MODEL_OUTPUTS, HEALTHY_KALMAN)
    assert result["dst_verdict"] == "Healthy", f"Expected Healthy, got {result['dst_verdict']}"

def test_unified_score_in_valid_range():
    """Unified health score must be 0-100."""
    from dst_fusion import DSTFusion
    fusion = DSTFusion()
    result = fusion.fuse(HEALTHY_MODEL_OUTPUTS, HEALTHY_KALMAN)
    score = result["unified_health_score"]
    assert 0 <= score <= 100, f"unified_health_score={score} out of [0, 100]"
