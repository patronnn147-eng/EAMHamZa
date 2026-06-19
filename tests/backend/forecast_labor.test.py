"""Test suite for labor forecast service."""
from modules.ml.services.labor_forecast import forecast_labor


def test_basic_demand():
    machine_forecasts = [
        {"expected_downtime_hours": 10.0},
        {"expected_downtime_hours": 6.0},
    ]
    result = forecast_labor(
        machine_forecasts=machine_forecasts,
        open_wo_count=5,
        avg_wo_hours=4.0,
        technician_count=3,
        horizon_days=30,
    )
    # demand = 16 (machines) + 20 (open WOs) = 36
    assert result["demand_hours"] == 36.0
    assert result["capacity_hours"] > 0
    assert 0 <= result["coverage_pct"] <= 100


def test_overload_flag():
    machine_forecasts = [{"expected_downtime_hours": 500.0}]
    result = forecast_labor(
        machine_forecasts=machine_forecasts,
        open_wo_count=0,
        avg_wo_hours=4.0,
        technician_count=1,
        horizon_days=7,
    )
    assert result["overload"] is True


def test_no_overload_when_plenty_capacity():
    machine_forecasts = [{"expected_downtime_hours": 2.0}]
    result = forecast_labor(
        machine_forecasts=machine_forecasts,
        open_wo_count=1,
        avg_wo_hours=4.0,
        technician_count=10,
        horizon_days=30,
    )
    assert result["overload"] is False


def test_zero_technicians_graceful():
    result = forecast_labor(
        machine_forecasts=[{"expected_downtime_hours": 8.0}],
        open_wo_count=2,
        avg_wo_hours=4.0,
        technician_count=0,
        horizon_days=30,
    )
    assert result["coverage_pct"] == 0.0
    assert result["overload"] is True


def test_breakdown_sums_to_demand():
    machine_forecasts = [{"expected_downtime_hours": 5.0}]
    result = forecast_labor(
        machine_forecasts=machine_forecasts,
        open_wo_count=3,
        avg_wo_hours=2.0,
        technician_count=2,
        horizon_days=30,
    )
    b = result["breakdown"]
    assert abs((b["predicted_failure_hours"] + b["open_wo_backlog_hours"]) - result["demand_hours"]) < 0.01
