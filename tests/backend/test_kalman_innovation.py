"""
Kalman innovation test: 95% of ||z_t - H@x_hat|| norms must be within 3σ.
Fails until Wave 1E (kalman_estimator.py) is implemented.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../app/ml-microservice/src'))

import numpy as np
import pytest

def test_kalman_innovation_within_3sigma():
    """95% of innovation norms must be < 3 * expected_innovation_sigma."""
    from kalman_estimator import KalmanStateEstimator
    np.random.seed(123)
    estimator = KalmanStateEstimator()
    estimator.reset()
    n_steps = 100
    innovation_norms = []
    # Simulate mildly degrading machine: HI goes 95 → 70 over 100 steps
    for t in range(n_steps):
        true_hi = 95 - 0.25 * t
        obs = {
            "rule_score":            true_hi + np.random.normal(0, 3),
            "ml_score":              true_hi + np.random.normal(0, 5),
            "survival_hi":           true_hi + np.random.normal(0, 4),
            "mahal_hi":              true_hi + np.random.normal(0, 2),
        }
        result = estimator.update(obs)
        innovation_norms.append(result["innovation_norm"])
    expected_sigma = np.std(innovation_norms) + 1e-9
    within_3sigma = np.array(innovation_norms) < 3 * expected_sigma
    fraction_ok = within_3sigma.mean()
    assert fraction_ok >= 0.95, (
        f"Only {fraction_ok*100:.1f}% of innovations within 3σ (need 95%)"
    )
