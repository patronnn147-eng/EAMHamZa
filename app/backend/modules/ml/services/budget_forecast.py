"""Budget forecast — pure function. Labor + parts reorder cost."""
from __future__ import annotations
import os
from typing import Any, Dict, List

LABOR_RATE_DEFAULT: float = float(os.getenv("LABOR_RATE_EUR", "50.0"))


def forecast_budget(
    labor_demand_hours: float,
    parts_reorder_items: List[Dict[str, Any]],
    labor_rate: float = LABOR_RATE_DEFAULT,
) -> Dict[str, Any]:
    """
    Pure function.
    labor_cost = labor_demand_hours * labor_rate
    parts_cost = sum(reorder_qty_suggested * unit_price) — unit_price defaults 0 if absent
    Returns {labor_cost, parts_cost, total, currency, breakdown[]}.
    """
    labor_cost = round(labor_demand_hours * labor_rate, 2)
    parts_cost = round(
        sum(
            float(i.get("reorder_qty_suggested", 0)) * float(i.get("unit_price", 0.0))
            for i in parts_reorder_items
        ),
        2,
    )
    total = round(labor_cost + parts_cost, 2)
    return {
        "labor_cost": labor_cost,
        "parts_cost": parts_cost,
        "total": total,
        "currency": "EUR",
        "breakdown": [
            {"label": "Main-d'œuvre", "value": labor_cost},
            {"label": "Pièces de rechange", "value": parts_cost},
        ],
    }
