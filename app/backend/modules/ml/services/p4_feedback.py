"""
Phase 4.3 — P4 flag-to-outcome tracking.
Mirrors p7_feedback.py's shape: triggered at work-order completion, writes
back onto the prediction-log row that made the call, non-fatal on failure.

Scope: precision-side signal only (did a flag get confirmed by a following
WO within N days) — the recall side (a real WO with no prior flag) needs a
full backtest across all flags/WOs, not a single-event hook; that's Phase 5
(P4 proxy-label backtest) territory, not this logging step.
"""

import json
import logging
from datetime import timedelta
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_DAYS = 14


async def record_p4_feedback(
    intervention_id: int,
    db: AsyncSession,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> Optional[Dict[str, Any]]:
    """
    For a completed intervention:
    1. Load the intervention's machine + when it actually happened.
    2. Find the most recent real (non-synthetic) P4 anomaly flag on that
       machine within `window_days` before it.
    3. If found, mark that flag's own prediction-log row as confirmed by a
       following WO — the "did this flag come true" signal P4 has never had.
    Returns the outcome dict, or None if there's nothing to correlate
    (no flag in window, or missing timestamps) — not an error, most
    completions won't have a preceding flag.
    """
    from models.ordres_intervention import OrdresIntervention
    from models.ml_prediction_log import MlPredictionLog

    itv_q = await db.execute(
        select(OrdresIntervention).where(OrdresIntervention.id == intervention_id)
    )
    itv = itv_q.scalar_one_or_none()
    if not itv or not itv.date_intervention:
        logger.debug(f"[P4-feedback] Intervention {intervention_id}: no date_intervention")
        return None

    wo_time = itv.date_intervention
    window_start = wo_time - timedelta(days=window_days)

    flag_q = await db.execute(
        select(MlPredictionLog)
        .where(
            and_(
                MlPredictionLog.machine_id == itv.machine_id,
                MlPredictionLog.is_anomaly.is_(True),
                MlPredictionLog.is_synthetic.is_(False),
                MlPredictionLog.p4_wo_outcome.is_(None),  # not already matched to an earlier WO
                MlPredictionLog.created_at >= window_start,
                MlPredictionLog.created_at <= wo_time,
            )
        )
        .order_by(desc(MlPredictionLog.created_at))
        .limit(1)
    )
    flag_log = flag_q.scalar_one_or_none()
    if not flag_log:
        logger.debug(
            f"[P4-feedback] No unmatched anomaly flag for machine {itv.machine_id} "
            f"in the {window_days}d before intervention {intervention_id}"
        )
        return None

    days_between = (wo_time - flag_log.created_at).total_seconds() / 86400.0
    outcome = {
        "flag_preceded_wo": True,
        "intervention_id": intervention_id,
        "days_between": round(days_between, 2),
        "window_days": window_days,
    }

    try:
        flag_log.p4_wo_outcome = json.dumps(outcome, default=str)
        await db.commit()
    except Exception as e:
        logger.warning(f"[P4-feedback] Failed to update prediction log {flag_log.id}: {e}")
        await db.rollback()
        return None

    logger.info(
        f"[P4-feedback] machine={itv.machine_id} itv={intervention_id} "
        f"flag_log={flag_log.id} days_between={outcome['days_between']}"
    )
    return outcome
