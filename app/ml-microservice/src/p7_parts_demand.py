import math


def p_fail_within(horizon: float, rul_days: float) -> float:
    """P(failure within `horizon` days) given remaining useful life.
    Exponential model, scale = rul_days. rul_days<=0 -> certain."""
    if rul_days <= 0:
        return 1.0
    return 1.0 - math.exp(-horizon / rul_days)


def survival_demand(failure_type_probs: dict, rul_days: float, horizon: float,
                    failure_part_map: dict, theta: float = 0.15) -> dict:
    """Expected demand per piece_id from condition signals.
    demand = sum_ft [ ft_prob * P(fail<=horizon) * p_used * expected_qty ]."""
    demand: dict = {}
    pf = p_fail_within(horizon, rul_days)
    for ft, prob in failure_type_probs.items():
        if prob < theta:
            continue
        for piece_id, stats in failure_part_map.get(ft, {}).items():
            contrib = prob * pf * stats.get("p_used", 0.0) * stats.get("expected_qty", 0.0)
            demand[piece_id] = demand.get(piece_id, 0.0) + contrib
    return demand


def croston_forecast(series: list, alpha: float = 0.4) -> float:
    """Croston intermittent-demand per-period forecast (size / interval)."""
    if not series or all(v == 0 for v in series):
        return 0.0
    z = None
    x = None
    gap = 1
    for v in series:
        if v != 0:
            z = v if z is None else alpha * v + (1 - alpha) * z
            x = gap if x is None else alpha * gap + (1 - alpha) * x
            gap = 1
        else:
            gap += 1
    if not z or not x:
        return 0.0
    return z / x


def stock_coverage_days(on_hand: float, expected_qty: float, horizon: int) -> "float | None":
    """Days of runway on_hand actually covers at the expected burn rate over
    the horizon. None when there's no expected demand at all (burn rate 0 —
    coverage is undefined, not infinite, since nothing's being consumed)."""
    daily_burn = expected_qty / horizon if horizon else 0.0
    if daily_burn <= 0:
        return None
    return on_hand / daily_burn


def build_parts_demand(survival: dict, consumable: dict, stock: dict,
                       horizon: int, source: str) -> dict:
    """Merge survival + consumable demand, join stock, compute shortfall/order/urgency.
    `stock`: piece_id -> {reference,name,on_hand,min_stock,is_consumable}."""
    items = []
    for pid in set(survival) | set(consumable):
        meta = stock.get(pid, {})
        expected = survival.get(pid, 0.0) + consumable.get(pid, 0.0)
        on_hand = float(meta.get("on_hand", 0.0))
        min_stock = float(meta.get("min_stock", 0) or 0)
        shortfall = max(0.0, expected - on_hand)
        order = max(shortfall, min_stock - on_hand, 0.0)
        driver = "condition" if (pid in survival and survival[pid] > 0) else "consumption"
        urgency = round(min(1.0, (shortfall / expected) if expected else 0.0), 4)
        # NOTE: coverage-based tempering was tried and removed — algebraically
        # identical to the shortfall/expected ratio above whenever shortfall>0
        # (both reduce to 1 - on_hand/expected), and coverage >= horizon
        # whenever shortfall==0, so it never changes urgency_score. Kept as
        # display-only information instead: "N days of runway" is genuinely
        # more actionable for a planner than "15 units short" even though it
        # carries no new signal for urgency scoring itself. A real
        # lead-time-adjustment would need a per-part reorder lead time (how
        # long delivery actually takes), which doesn't exist in the schema
        # yet — that's a data-collection gap, not a formula fix.
        coverage = stock_coverage_days(on_hand, expected, horizon)
        items.append({
            "piece_id": pid, "reference": meta.get("reference", ""),
            "name": meta.get("name", ""), "expected_qty": round(expected, 3),
            "on_hand": on_hand, "min_stock": int(min_stock), "shortfall": round(shortfall, 3),
            "stock_coverage_days": round(coverage, 1) if coverage is not None else None,
            "urgency_score": urgency, "recommended_order_qty": round(order, 3), "driver": driver,
        })
    items.sort(key=lambda i: (-i["urgency_score"], -i["shortfall"]))
    return {"horizon_days": horizon, "source": source, "items": items}
