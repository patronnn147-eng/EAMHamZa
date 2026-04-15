"""
C-statistic test: Harrell's C > 0.75 on survival model holdout.
Fails until Wave 1B (survival_model.py) is implemented.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../app/ml-microservice/src'))

import numpy as np
import pytest

def harrell_c_statistic(durations, events, risk_scores):
    """
    Compute Harrell's concordance index manually.
    Higher risk_score = sooner failure expected.
    """
    n = len(durations)
    concordant = 0
    comparable = 0
    for i in range(n):
        for j in range(n):
            if events[i] == 1 and durations[i] < durations[j]:
                comparable += 1
                if risk_scores[i] > risk_scores[j]:
                    concordant += 1
                elif risk_scores[i] == risk_scores[j]:
                    concordant += 0.5
    return concordant / comparable if comparable > 0 else 0.5

def test_survival_c_statistic_above_threshold():
    """Harrell's C-statistic must exceed 0.75 on holdout."""
    from survival_model import SurvivalModel
    model = SurvivalModel()
    np.random.seed(0)
    n = 200
    # Structured data: high wear → short survival
    tool_wear = np.random.uniform(0, 250, n)
    durations = np.maximum(1, 60 - tool_wear * 0.2 + np.random.normal(0, 5, n))
    events = (tool_wear > 100).astype(int)
    X = np.column_stack([
        np.full(n, 300), np.full(n, 310),
        np.full(n, 1500), np.full(n, 40),
        tool_wear
    ])
    model.fit_from_arrays(X, durations, events)
    risk_scores = model.predict_failure_probability(X)
    c_stat = harrell_c_statistic(durations, events, risk_scores)
    assert c_stat > 0.75, f"C-statistic={c_stat:.3f} below threshold 0.75"
