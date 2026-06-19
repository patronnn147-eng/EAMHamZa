import random
from modules.ml.services.drift import population_stability_index, compute_drift


def test_psi_zero_for_identical():
    xs = [float(i % 10) for i in range(200)]
    assert population_stability_index(xs, xs) < 0.01


def test_psi_large_for_shift():
    random.seed(0)
    base = [random.gauss(0, 1) for _ in range(500)]
    shifted = [random.gauss(3, 1) for _ in range(500)]
    assert population_stability_index(base, shifted) > 0.25


def test_compute_drift_stable_vs_drifting():
    sensors = ("torque",)
    base = [{"torque": 40.0 + (i % 5)} for i in range(50)]
    same = [{"torque": 40.0 + (i % 5)} for i in range(50)]
    assert compute_drift(base, same, sensors)["verdict"] == "stable"
    shifted = [{"torque": 80.0 + (i % 5)} for i in range(50)]
    assert compute_drift(base, shifted, sensors)["verdict"] == "drifting"


def test_insufficient_data():
    assert compute_drift([], [], ("torque",))["verdict"] == "insufficient_data"
