"""
CUSUM drift test: alarm must fire within 5 samples after +2sigma step injection.
Fails until Wave 1D (anomaly_cusum.py) is implemented.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../app/ml-microservice/src'))

import numpy as np
import pytest

def test_cusum_alarms_within_5_samples_after_step():
    """After a +2σ step change, CUSUM must alarm within 5 samples."""
    from anomaly_cusum import CUSUMDetector
    mu_0 = 300.0    # baseline mean (air_temperature)
    sigma = 5.0     # baseline std
    k = 0.5 * sigma  # allowance
    h = 5.0 * sigma  # decision threshold
    detector = CUSUMDetector(k=k, h=h)
    # Inject sustained +2σ step
    step_value = mu_0 + 2.0 * sigma
    alarm_t = None
    for t in range(10):
        if detector.update(step_value, mu_0):
            alarm_t = t
            break
    assert alarm_t is not None, "CUSUM never alarmed on +2σ step"
    assert alarm_t <= 4, f"CUSUM alarm at t={alarm_t}, expected t<=4"

def test_cusum_no_alarm_on_normal_data():
    """CUSUM must NOT alarm on in-control data (within 1σ noise)."""
    from anomaly_cusum import CUSUMDetector
    np.random.seed(42)
    mu_0 = 300.0
    sigma = 5.0
    detector = CUSUMDetector(k=0.5*sigma, h=5*sigma)
    alarmed = False
    for _ in range(100):
        x = np.random.normal(mu_0, sigma * 0.5)  # half-sigma noise
        if detector.update(x, mu_0):
            alarmed = True
            break
    assert not alarmed, "CUSUM false alarm on in-control data"
