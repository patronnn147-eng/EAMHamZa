"""
Calibration test: Survival model ECE < 0.05
Fails until Wave 1B (survival_model.py) is implemented.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../app/ml-microservice/src'))

import numpy as np
import pytest

def compute_ece(y_true, y_prob, n_bins=10):
    """Expected Calibration Error over n equal-width bins."""
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (y_prob >= bins[i]) & (y_prob < bins[i+1])
        if mask.sum() == 0:
            continue
        bin_acc  = y_true[mask].mean()
        bin_conf = y_prob[mask].mean()
        ece += mask.sum() * abs(bin_acc - bin_conf)
    return ece / len(y_true)

def test_survival_model_ece_below_threshold():
    """ECE of survival model on holdout set must be < 0.05."""
    from survival_model import SurvivalModel
    model = SurvivalModel()
    # Synthetic holdout: 100 samples, columns air, process, rpm, torque, wear
    np.random.seed(42)
    n = 100
    X = np.column_stack([
        np.random.uniform(295, 305, n),   # air_temp
        np.random.uniform(305, 315, n),   # process_temp
        np.random.uniform(1300, 1700, n), # rpm
        np.random.uniform(35, 45, n),     # torque
        np.random.uniform(0, 200, n),     # tool_wear
    ])
    # Events: failure = 1 when tool_wear > 150 (synthetic rule)
    events = (X[:, 4] > 150).astype(int)
    durations = np.random.uniform(1, 60, n)

    model.fit_from_arrays(X, durations, events)
    probs = model.predict_failure_probability(X)
    ece = compute_ece(events.astype(float), probs)
    assert ece < 0.05, f"ECE={ece:.4f} exceeds threshold 0.05"
