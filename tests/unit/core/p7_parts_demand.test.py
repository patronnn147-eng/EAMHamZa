import math
from app.ml_microservice.src.p7_parts_demand import (
    p_fail_within, survival_demand, croston_forecast, build_parts_demand,
)

# p_fail_within
def test_p_fail_within_half_life():
    assert math.isclose(p_fail_within(horizon=30, rul_days=30), 1 - math.e**-1, rel_tol=1e-6)

def test_p_fail_within_zero_rul_is_certain():
    assert p_fail_within(horizon=30, rul_days=0) == 1.0

def test_p_fail_within_huge_rul_is_small():
    assert p_fail_within(horizon=1, rul_days=10_000) < 0.001

# survival_demand
def test_survival_demand_weights_by_prob_and_qty():
    fmap = {"TWF": {7: {"p_used": 1.0, "expected_qty": 2.0}}}
    out = survival_demand({"TWF": 1.0}, rul_days=30, horizon=30, failure_part_map=fmap, theta=0.15)
    assert abs(out[7] - (1 - math.e**-1) * 2.0) < 1e-3

def test_survival_demand_skips_below_theta():
    fmap = {"TWF": {7: {"p_used": 1.0, "expected_qty": 2.0}}}
    assert survival_demand({"TWF": 0.1}, 30, 30, fmap, theta=0.15) == {}

# croston_forecast
def test_croston_constant_demand_recovers_rate():
    assert abs(croston_forecast([2, 2, 2, 2, 2], alpha=0.4) - 2.0) < 0.3

def test_croston_intermittent_positive_rate():
    rate = croston_forecast([0, 0, 5, 0, 0, 5, 0], alpha=0.4)
    assert 0 < rate < 5

def test_croston_all_zero_returns_zero():
    assert croston_forecast([0, 0, 0], alpha=0.4) == 0.0

# build_parts_demand
def test_build_parts_demand_shortfall_and_order():
    survival = {7: 2.0}; consumable = {}
    stock = {7: {"reference": "BRG-7", "name": "Bearing", "on_hand": 1.0, "min_stock": 2, "is_consumable": False}}
    out = build_parts_demand(survival, consumable, stock, horizon=30, source="p7_model")
    item = out["items"][0]
    assert out["horizon_days"] == 30 and out["source"] == "p7_model"
    assert item["piece_id"] == 7 and item["expected_qty"] == 2.0
    assert item["shortfall"] == 1.0
    assert item["recommended_order_qty"] == 1.0
    assert item["driver"] == "condition"

def test_build_parts_demand_consumable_driver():
    out = build_parts_demand({}, {9: 3.0},
        {9: {"reference": "OIL", "name": "Oil", "on_hand": 10, "min_stock": 5, "is_consumable": True}},
        30, "p7_model")
    assert out["items"][0]["driver"] == "consumption"
    assert out["items"][0]["shortfall"] == 0.0
