"""
Monotonicity test: HI must be non-increasing as tool_wear increases.
Tolerance epsilon = 2.0 (noise tolerance).
Fails until Wave 1A (health_index.py) is implemented.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../app/ml-microservice/src'))

import numpy as np
import pytest

def test_health_index_monotone_under_wear_progression():
    """HI(t) <= HI(t-1) + epsilon for increasing tool_wear."""
    from health_index import MahalanobisHealthIndex
    epsilon = 2.0
    # Train on healthy data (low wear)
    np.random.seed(7)
    n_healthy = 300
    healthy = np.column_stack([
        np.random.uniform(297, 301, n_healthy),  # air_temp
        np.random.uniform(307, 311, n_healthy),  # process_temp
        np.random.uniform(1450, 1550, n_healthy), # rpm
        np.random.uniform(38, 42, n_healthy),    # torque
        np.random.uniform(0, 30, n_healthy),     # tool_wear (fresh tools)
    ])
    model = MahalanobisHealthIndex()
    model.fit(healthy)
    # Test wear progression: 0, 50, 100, 150, 200, 250 minutes
    wear_levels = [0, 50, 100, 150, 200, 250]
    hi_sequence = []
    for wear in wear_levels:
        x = np.array([[300, 310, 1500, 40, wear]])
        out = model.score(x[0])
        hi_sequence.append(out["health_index"])
    for i in range(1, len(hi_sequence)):
        assert hi_sequence[i] <= hi_sequence[i-1] + epsilon, (
            f"HI not monotone at wear={wear_levels[i]}: "
            f"HI[{i}]={hi_sequence[i]:.2f} > HI[{i-1}]={hi_sequence[i-1]:.2f} + {epsilon}"
        )
