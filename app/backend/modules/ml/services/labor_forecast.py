"""Labor demand/capacity forecast — pure function."""

from __future__ import annotations
from typing import Any, Dict, List


def forecast_labor(
    machine_forecasts: List[Dict[str, Any]],
    open_wo_count: int,
    avg_wo_hours: float,
    technician_count: int,
    horizon_days: int,
) -> Dict[str, Any]:
    """
    Pure function to forecast labor demand vs capacity.

    demand  = sum(expected_downtime_hours) + open_wo_count * avg_wo_hours
    capacity = technician_count * 8h * workdays (horizon * 5/7)

    Returns {demand_hours, capacity_hours, coverage_pct, overload, breakdown}.
    """
    predicted_hours = sum(
        float(m.get("expected_downtime_hours", 0)) for m in machine_forecasts
    )
    backlog_hours = float(open_wo_count) * float(avg_wo_hours)
    demand = round(predicted_hours + backlog_hours, 1)

    workdays = max(1, round(horizon_days * 5 / 7))
    capacity = float(technician_count * 8 * workdays)

    if technician_count == 0 or capacity == 0:
        coverage = 0.0
    else:
        coverage = round(min(100.0, capacity / max(demand, 0.01) * 100.0), 1)

    return {
        "demand_hours": demand,
        "capacity_hours": capacity,
        "coverage_pct": coverage,
        "overload": demand > capacity,
        "technician_count": technician_count,
        "workdays": workdays,
        "breakdown": {
            "predicted_failure_hours": round(predicted_hours, 1),
            "open_wo_backlog_hours": round(backlog_hours, 1),
        },
    }
