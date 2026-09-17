"""
P7.5 — Machine Readiness Score + Maintenance Timeline.
Blends unified_health_score + inventory coverage + procurement risk
+ recent maintenance into a 0-100 readiness index.
Timeline derives ordered events from existing DB timestamps — no new table.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_

logger = logging.getLogger(__name__)

# ── Pure helpers ──────────────────────────────────────────────────────────


def compute_readiness_score(
    unified_health_score: Optional[float],
    parts_shortage_active: bool,
    parts_demand_items: List[Dict[str, Any]],
    days_since_last_maintenance: Optional[float],
) -> Dict[str, Any]:
    """
    Blend 4 signals into a 0-100 readiness score.
    All weights documented; missing inputs degrade gracefully.

    Weights:
      40% — unified health score (ML DST fusion)
      30% — inventory coverage (fraction of demanded parts in stock)
      20% — procurement risk (parts shortage active = penalty)
      10% — maintenance recency (recent maintenance = positive)
    """
    # ── Component 1: health (0-100 → 0-40) ──────────────────────────────
    health_raw = max(
        0.0, min(100.0, 50.0 if unified_health_score is None else unified_health_score)
    )
    health_contrib = health_raw * 0.40

    # ── Component 2: inventory coverage (0-1 → 0-30) ────────────────────
    if not parts_demand_items:
        cov_score = 100.0  # no demand = fully covered
    else:
        total_demand = sum(i.get("expected_qty", 0) or 0 for i in parts_demand_items)
        total_shortfall = sum(i.get("shortfall", 0) or 0 for i in parts_demand_items)
        if total_demand <= 0:
            cov_score = 100.0
        else:
            cov_score = max(0.0, 100.0 * (1 - total_shortfall / total_demand))
    cov_contrib = cov_score * 0.30

    # ── Component 3: procurement risk (0-20) ────────────────────────────
    # Active shortage = penalty; no shortage = full marks
    proc_score = 0.0 if parts_shortage_active else 100.0
    proc_contrib = proc_score * 0.20

    # ── Component 4: maintenance recency (0-100 → 0-10) ─────────────────
    if days_since_last_maintenance is None:
        rec_score = 50.0  # unknown — neutral
    elif days_since_last_maintenance <= 7:
        rec_score = 100.0
    elif days_since_last_maintenance <= 30:
        rec_score = 80.0
    elif days_since_last_maintenance <= 90:
        rec_score = 60.0
    elif days_since_last_maintenance <= 180:
        rec_score = 30.0
    else:
        rec_score = 10.0
    rec_contrib = rec_score * 0.10

    total = round(health_contrib + cov_contrib + proc_contrib + rec_contrib, 1)

    return {
        "readiness_score": total,
        "breakdown": {
            "health": round(health_contrib, 1),
            "inventory_coverage": round(cov_contrib, 1),
            "procurement_risk": round(proc_contrib, 1),
            "maintenance_recency": round(rec_contrib, 1),
        },
        "weights": {
            "health": 0.40,
            "inventory_coverage": 0.30,
            "procurement_risk": 0.20,
            "maintenance_recency": 0.10,
        },
        "inputs": {
            "unified_health_score": round(health_raw, 1),
            "inventory_coverage_pct": round(cov_score, 1),
            "parts_shortage_active": parts_shortage_active,
            "days_since_last_maintenance": days_since_last_maintenance,
        },
    }


def build_timeline_events(
    prediction_log_rows: List[Dict],
    work_order_rows: List[Dict],
    intervention_rows: List[Dict],
    alert_rows: List[Dict],
) -> List[Dict[str, Any]]:
    """
    Merge events from multiple sources into a chronological timeline.
    Pure function — accepts pre-fetched dicts so it's fully testable.
    Each event: {date: str, type: str, label: str, detail: str|None}
    """
    events: List[Dict[str, Any]] = []

    def _add(date_val, event_type: str, label: str, detail: Optional[str] = None):
        if date_val is None:
            return
        if isinstance(date_val, datetime):
            date_str = date_val.isoformat()
        else:
            date_str = str(date_val)
        events.append(
            {"date": date_str, "type": event_type, "label": label, "detail": detail}
        )

    for row in prediction_log_rows:
        _add(
            row.get("created_at"),
            "forecast",
            "AI forecast generated",
            f"Failure probability: {row.get('failure_probability', 0):.0f}%  RUL: {row.get('rul_days', '?')} days",
        )

    for row in alert_rows:
        _add(
            row.get("created_at"),
            "alert",
            "Parts shortage alert",
            row.get("message", "Parts below required stock"),
        )

    for row in work_order_rows:
        _add(
            row.get("created_at"),
            "wo_created",
            f"Work order created (#{row.get('id', '')})",
            row.get("titre", ""),
        )
        _add(
            row.get("date_validation"),
            "wo_approved",
            f"Work order approved (#{row.get('id', '')})",
            f"Status: {row.get('statut', '')}",
        )
        _add(
            row.get("date_debut"),
            "wo_started",
            f"Work order started (#{row.get('id', '')})",
            None,
        )
        _add(
            row.get("date_fin"),
            "wo_completed",
            f"Work order completed (#{row.get('id', '')})",
            None,
        )

    for row in intervention_rows:
        _add(
            row.get("approved_at"),
            "itv_approved",
            "Intervention approved",
            row.get("machine_category", ""),
        )
        _add(row.get("date_fin"), "itv_completed", "Intervention completed", None)

    # Deduplicate identical (date, type) pairs and sort chronologically
    seen: set = set()
    unique: List[Dict] = []
    for e in events:
        key = (e["date"], e["type"])
        if key not in seen:
            seen.add(key)
            unique.append(e)

    unique.sort(key=lambda e: e["date"])
    return unique


# ── Async DB fetchers ─────────────────────────────────────────────────────


async def get_readiness_for_machine(
    machine_id: int,
    unified_health_score: Optional[float],
    parts_demand: Optional[Dict[str, Any]],
    db: AsyncSession,
) -> Dict[str, Any]:
    """Compute readiness score from live DB state."""
    from models.alertes import Alert, AlertType
    from models.ordres_intervention import Ordres_intervention

    # Is there an active PARTS_SHORTAGE alert?
    alert_q = await db.execute(
        select(Alert).where(
            and_(
                Alert.machine_id == machine_id,
                Alert.alert_type == AlertType.PARTS_SHORTAGE,
                Alert.is_active,
            )
        )
    )
    shortage_active = alert_q.scalar_one_or_none() is not None

    # Days since last completed intervention
    itv_q = await db.execute(
        select(Ordres_intervention)
        .where(
            and_(
                Ordres_intervention.machine_id == machine_id,
                Ordres_intervention.statut == "VALIDATED",
            )
        )
        .order_by(desc(Ordres_intervention.date_fin))
        .limit(1)
    )
    last_itv = itv_q.scalar_one_or_none()
    days_since: Optional[float] = None
    if last_itv and last_itv.date_fin:
        now_aware = datetime.now(timezone.utc)
        fin_aware = (
            last_itv.date_fin.replace(tzinfo=timezone.utc)
            if last_itv.date_fin.tzinfo is None
            else last_itv.date_fin
        )
        days_since = (now_aware - fin_aware).days

    items = (parts_demand or {}).get("items", [])
    return compute_readiness_score(
        unified_health_score, shortage_active, items, days_since
    )


async def get_timeline_for_machine(
    machine_id: int,
    db: AsyncSession,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Fetch timeline events from existing timestamps — no new table."""
    from models.ml_prediction_log import MlPredictionLog
    from models.ordres_travail import Ordres_travail
    from models.ordres_intervention import Ordres_intervention
    from models.alertes import Alert, AlertType

    # Last 10 prediction logs
    pred_q = await db.execute(
        select(MlPredictionLog)
        .where(MlPredictionLog.machine_id == machine_id)
        .order_by(desc(MlPredictionLog.created_at))
        .limit(10)
    )
    pred_rows = [
        {
            "created_at": r.created_at,
            "failure_probability": r.failure_probability,
            "rul_days": r.rul_days,
        }
        for r in pred_q.scalars().all()
    ]

    # Work orders
    wo_q = await db.execute(
        select(Ordres_travail)
        .where(Ordres_travail.machine_id == machine_id)
        .order_by(desc(Ordres_travail.created_at))
        .limit(10)
    )
    wo_rows = [
        {
            "id": r.id,
            "titre": r.titre,
            "statut": r.statut.value if hasattr(r.statut, "value") else str(r.statut),
            "created_at": r.created_at,
            "date_validation": r.date_validation,
            "date_debut": r.date_debut,
            "date_fin": r.date_fin,
        }
        for r in wo_q.scalars().all()
    ]

    # Interventions
    itv_q = await db.execute(
        select(Ordres_intervention)
        .where(Ordres_intervention.machine_id == machine_id)
        .order_by(desc(Ordres_intervention.created_at))
        .limit(10)
    )
    itv_rows = [
        {
            "approved_at": r.approved_at,
            "date_fin": r.date_fin,
            "machine_category": r.machine_category,
        }
        for r in itv_q.scalars().all()
    ]

    # PARTS_SHORTAGE alerts
    alert_q = await db.execute(
        select(Alert)
        .where(
            and_(
                Alert.machine_id == machine_id,
                Alert.alert_type == AlertType.PARTS_SHORTAGE,
            )
        )
        .order_by(desc(Alert.created_at))
        .limit(5)
    )
    alert_rows = [
        {"created_at": r.created_at, "message": r.message}
        for r in alert_q.scalars().all()
    ]

    events = build_timeline_events(pred_rows, wo_rows, itv_rows, alert_rows)
    return events[-limit:]  # return most recent N events
