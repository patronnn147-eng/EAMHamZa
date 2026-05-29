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
        items.append({
            "piece_id": pid, "reference": meta.get("reference", ""),
            "name": meta.get("name", ""), "expected_qty": round(expected, 3),
            "on_hand": on_hand, "min_stock": int(min_stock), "shortfall": round(shortfall, 3),
            "urgency_score": urgency, "recommended_order_qty": round(order, 3), "driver": driver,
        })
    items.sort(key=lambda i: (-i["urgency_score"], -i["shortfall"]))
    return {"horizon_days": horizon, "source": source, "items": items}
