import os
from modules.ml.services.budget_forecast import forecast_budget, LABOR_RATE_DEFAULT


def test_labor_only():
    result = forecast_budget(labor_demand_hours=10.0, parts_reorder_items=[])
    assert result["labor_cost"] == round(10.0 * LABOR_RATE_DEFAULT, 2)
    assert result["parts_cost"] == 0.0
    assert result["total"] == result["labor_cost"]
    assert result["currency"] == "EUR"


def test_parts_cost_aggregated():
    items = [
        {"reorder_qty_suggested": 3, "unit_price": 20.0},
        {"reorder_qty_suggested": 1, "unit_price": 150.0},
    ]
    result = forecast_budget(labor_demand_hours=0.0, parts_reorder_items=items)
    assert result["parts_cost"] == 3 * 20.0 + 1 * 150.0


def test_missing_unit_price_defaults_zero():
    items = [{"reorder_qty_suggested": 5}]  # no unit_price key
    result = forecast_budget(labor_demand_hours=0.0, parts_reorder_items=items)
    assert result["parts_cost"] == 0.0


def test_total_equals_labor_plus_parts():
    items = [{"reorder_qty_suggested": 2, "unit_price": 50.0}]
    result = forecast_budget(labor_demand_hours=8.0, parts_reorder_items=items)
    assert abs(result["total"] - (result["labor_cost"] + result["parts_cost"])) < 0.01


def test_custom_labor_rate():
    result = forecast_budget(labor_demand_hours=4.0, parts_reorder_items=[], labor_rate=100.0)
    assert result["labor_cost"] == 400.0


def test_breakdown_has_two_entries():
    result = forecast_budget(labor_demand_hours=5.0, parts_reorder_items=[])
    assert len(result["breakdown"]) == 2
    labels = {e["label"] for e in result["breakdown"]}
    assert "Main-d'œuvre" in labels
    assert "Pièces de rechange" in labels
