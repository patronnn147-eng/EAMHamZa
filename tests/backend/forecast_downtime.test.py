from modules.ml.services.downtime_forecast import estimate_downtime_hours


def test_high_risk_machine():
    result = estimate_downtime_hours(rul_days=5, failure_prob=85, horizon_days=30)
    assert result["p_failure"] > 0.7
    assert result["expected_downtime_hours"] > 0
    assert result["horizon_days"] == 30


def test_healthy_machine():
    result = estimate_downtime_hours(rul_days=200, failure_prob=5, horizon_days=30)
    assert result["p_failure"] < 0.2


def test_p_failure_clamps_to_one():
    result = estimate_downtime_hours(rul_days=0, failure_prob=100, horizon_days=7)
    assert result["p_failure"] <= 1.0


def test_short_horizon_lower_than_long():
    r7 = estimate_downtime_hours(rul_days=20, failure_prob=50, horizon_days=7)
    r60 = estimate_downtime_hours(rul_days=20, failure_prob=50, horizon_days=60)
    assert r7["p_failure"] <= r60["p_failure"]


def test_custom_repair_hours():
    result = estimate_downtime_hours(rul_days=5, failure_prob=80, horizon_days=30, avg_repair_hours=12.0)
    assert result["expected_downtime_hours"] == round(result["p_failure"] * 12.0, 2)
