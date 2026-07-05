"""
Demand Forecast Service — Inventory × ML cross-signal.

Crosses RUL predictions from MlPredictionLog with spare parts stock levels
and historical consumption from mouvement_stock to produce a ranked reorder list.

No trained model — deterministic algorithm, cached 1 hour.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.ml_prediction_log import MlPredictionLog
from models.pieces import Piece
from models.piece_machine import piece_machine
from models.stock import Stock
from models.mouvement_stock import MouvementStock

logger = logging.getLogger(__name__)

# In-memory cache (same pattern as fleet dashboard)
_forecast_cache: Dict[str, Any] = {
    "data": None,
    "timestamp": None,
    "ttl_seconds": 3600,  # 1 hour
}

_DEFAULT_CONSUMPTION_RATE = 1.0  # units / intervention when no history exists
_RUL_HORIZON_DAYS = 90  # beyond this RUL the machine contributes 0 weight


def _urgency_score(
    rul_days: float,
    failure_probability: float,
    current_qty: int,
    consumption_rate: float,
    min_stock: int,
) -> float:
    """
    Composite urgency score [0, 1].

    Weights:
      - RUL        40%: closer to failure → higher
      - Stock      40%: lower stock relative to expected demand → higher
      - Fail prob  20%: higher probability → higher
    """
    rul_weight = max(0.0, 1.0 - rul_days / _RUL_HORIZON_DAYS)
    expected_demand = max(1.0, consumption_rate * 3)
    stock_weight = max(0.0, 1.0 - current_qty / expected_demand)
    prob_weight = min(1.0, failure_probability / 100.0)

    score = (rul_weight * 0.4) + (stock_weight * 0.4) + (prob_weight * 0.2)
    return round(min(1.0, max(0.0, score)), 4)


def _urgency_label(score: float) -> str:
    if score >= 0.7:
        return "URGENT"
    if score >= 0.4:
        return "SOON"
    return "MONITOR"


def _days_until_stockout(
    current_qty: int, consumption_rate_per_month: float
) -> Optional[int]:
    """Estimate days until stockout given monthly consumption rate."""
    if consumption_rate_per_month <= 0:
        return None
    daily_rate = consumption_rate_per_month / 30.0
    if daily_rate <= 0:
        return None
    return int(current_qty / daily_rate)


async def _get_consumption_rates(db: AsyncSession) -> Dict[int, tuple]:
    """
    Returns {piece_id: (rate_per_month, data_quality)}
    rate_per_month = average monthly 'out' quantity from mouvement_stock.
    data_quality = "real" | "estimated"
    """
    # Count total 'out' quantity per piece and earliest/latest date
    stmt = (
        select(
            MouvementStock.piece_id,
            func.sum(MouvementStock.quantity).label("total_out"),
            func.min(MouvementStock.created_at).label("first_date"),
            func.max(MouvementStock.created_at).label("last_date"),
        )
        .where(MouvementStock.movement_type == "out")
        .group_by(MouvementStock.piece_id)
    )
    result = await db.execute(stmt)
    rows = result.fetchall()

    rates: Dict[int, tuple] = {}
    now = datetime.now(timezone.utc)

    for piece_id, total_out, first_date, last_date in rows:
        if first_date is None or total_out is None or total_out == 0:
            continue
        # Compute span in months (minimum 1 month to avoid division extremes)
        if first_date.tzinfo is None:
            first_date = first_date.replace(tzinfo=timezone.utc)
        span_days = max(30, (now - first_date).days)
        span_months = span_days / 30.0
        rate = float(total_out) / span_months
        rates[piece_id] = (rate, "real")

    return rates


async def compute_demand_forecast(
    db: AsyncSession,
    horizon_days: int = 60,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Compute ranked reorder list. Results cached for 1 hour.
    horizon_days: only include machines with RUL <= this value.
    limit: top N items to return.
    """
    now = datetime.now(timezone.utc)

    # Check cache
    if (
        _forecast_cache["data"] is not None
        and _forecast_cache["timestamp"] is not None
        and (now - _forecast_cache["timestamp"]).total_seconds()
        < _forecast_cache["ttl_seconds"]
    ):
        cached = _forecast_cache["data"]
        # Apply horizon/limit on cached data (they may differ per request)
        items = [
            i
            for i in cached["_all_items"]
            if any(m["rul_days"] <= horizon_days for m in i["machines_affected"])
        ]
        return _build_response(items[:limit], horizon_days, now)

    try:
        # 1. Latest ML prediction per machine
        latest_log_subq = (
            select(
                MlPredictionLog.machine_id,
                func.max(MlPredictionLog.id).label("max_id"),
            )
            .group_by(MlPredictionLog.machine_id)
            .subquery()
        )
        logs_result = await db.execute(
            select(MlPredictionLog).join(
                latest_log_subq,
                (MlPredictionLog.machine_id == latest_log_subq.c.machine_id)
                & (MlPredictionLog.id == latest_log_subq.c.max_id),
            )
        )
        logs_by_machine: Dict[int, MlPredictionLog] = {
            row.machine_id: row for row in logs_result.scalars().all()
        }

        # 2. All piece→machine links
        pm_result = await db.execute(
            select(piece_machine.c.piece_id, piece_machine.c.machine_id)
        )
        pm_rows = pm_result.fetchall()

        # Build {piece_id: [machine_id, ...]}
        pieces_to_machines: Dict[int, List[int]] = {}
        for p_id, m_id in pm_rows:
            pieces_to_machines.setdefault(p_id, []).append(m_id)

        if not pieces_to_machines:
            result = {
                "items": [],
                "total_urgent": 0,
                "total_monitor": 0,
                "generated_at": now.isoformat(),
                "horizon_days": horizon_days,
                "_all_items": [],
            }
            _forecast_cache["data"] = result
            _forecast_cache["timestamp"] = now
            return result

        piece_ids = list(pieces_to_machines.keys())

        # 3. Stock levels for these pieces
        stock_result = await db.execute(
            select(Stock.piece_id, Stock.quantity).where(Stock.piece_id.in_(piece_ids))
        )
        stock_by_piece: Dict[int, float] = {
            row[0]: float(row[1]) for row in stock_result.fetchall()
        }

        # 4. Piece metadata (name, min_stock)
        pieces_result = await db.execute(
            select(Piece.id, Piece.name, Piece.min_stock).where(Piece.id.in_(piece_ids))
        )
        piece_meta: Dict[int, tuple] = {
            row[0]: (row[1], int(row[2] or 5)) for row in pieces_result.fetchall()
        }

        # 5. Consumption rates from movement history
        consumption_rates = await _get_consumption_rates(db)

        # 6. Build forecast items
        # Machine name lookup
        from models.machines import Machines

        machines_result = await db.execute(select(Machines.id, Machines.nom))
        machine_names: Dict[int, str] = {
            row[0]: row[1] for row in machines_result.fetchall()
        }

        # Per-piece: aggregate across all linked machines
        all_items: List[Dict[str, Any]] = []

        for piece_id, machine_ids in pieces_to_machines.items():
            if piece_id not in piece_meta:
                continue

            piece_name, min_stock = piece_meta[piece_id]
            current_qty = stock_by_piece.get(piece_id, 0)
            rate, data_quality = consumption_rates.get(
                piece_id, (_DEFAULT_CONSUMPTION_RATE, "estimated")
            )

            # Only consider machines with actual ML log data
            affected_machines = []
            max_urgency = 0.0
            max_fail_prob = 0.0

            for m_id in machine_ids:
                log = logs_by_machine.get(m_id)
                if log is None:
                    continue
                rul = (
                    float(log.rul_days)
                    if log.rul_days is not None
                    else _RUL_HORIZON_DAYS
                )
                fail_prob = float(log.failure_probability or 0.0)
                score = _urgency_score(rul, fail_prob, current_qty, rate, min_stock)
                if score > max_urgency:
                    max_urgency = score
                if fail_prob > max_fail_prob:
                    max_fail_prob = fail_prob
                affected_machines.append(
                    {
                        "id": m_id,
                        "name": machine_names.get(m_id, f"Machine {m_id}"),
                        "rul_days": round(rul, 1),
                        "urgency_score": score,
                    }
                )

            if not affected_machines:
                continue

            # Sort machines by urgency descending within the item
            affected_machines.sort(key=lambda x: x["urgency_score"], reverse=True)

            projected_demand = max(1, round(rate * len(affected_machines)))
            reorder_qty = max(projected_demand, min_stock) + max(1, round(rate))
            days_out = _days_until_stockout(current_qty, rate)

            all_items.append(
                {
                    "piece_id": piece_id,
                    "piece_name": piece_name,
                    "current_qty": current_qty,
                    "min_stock": min_stock,
                    "urgency_score": max_urgency,
                    "urgency_label": _urgency_label(max_urgency),
                    "projected_demand": projected_demand,
                    "reorder_qty_suggested": reorder_qty,
                    "days_until_stockout": days_out,
                    "consumption_data": data_quality,
                    "machines_affected": [
                        {"id": m["id"], "name": m["name"], "rul_days": m["rul_days"]}
                        for m in affected_machines
                    ],
                }
            )

        # Sort by urgency descending
        all_items.sort(key=lambda x: x["urgency_score"], reverse=True)

        _forecast_cache["data"] = {
            "_all_items": all_items,
            "generated_at": now.isoformat(),
        }
        _forecast_cache["timestamp"] = now

        # Apply horizon filter + limit
        filtered = [
            i
            for i in all_items
            if any(m["rul_days"] <= horizon_days for m in i["machines_affected"])
        ]
        return _build_response(filtered[:limit], horizon_days, now)

    except Exception as e:
        logger.error(f"Error computing demand forecast: {str(e)}", exc_info=True)
        raise


def _build_response(
    items: List[Dict], horizon_days: int, ts: datetime
) -> Dict[str, Any]:
    total_urgent = sum(1 for i in items if i["urgency_label"] == "URGENT")
    total_monitor = sum(1 for i in items if i["urgency_label"] in ("SOON", "MONITOR"))
    return {
        "generated_at": ts.isoformat(),
        "horizon_days": horizon_days,
        "total_urgent": total_urgent,
        "total_monitor": total_monitor,
        "items": items,
    }


def invalidate_forecast_cache() -> None:
    """Call when stock changes to bust the 1-hour cache."""
    _forecast_cache["data"] = None
    _forecast_cache["timestamp"] = None
