"""
P7.6 — Feedback closure.
Compares P7 predicted parts vs actual consumed parts from completed
interventions, records match/error, queues P7 for retraining.

Triggered after a work order is completed and consumed_pieces are logged.
Pure comparison functions are testable without DB.
"""

import json
import logging
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

logger = logging.getLogger(__name__)


# ── Pure comparison helpers ───────────────────────────────────────────────


def parse_parts_demand_json(json_str: Optional[str]) -> Optional[Dict[str, Any]]:
    """Safe deserialization from Text column."""
    if not json_str:
        return None
    try:
        return json.loads(json_str)
    except Exception:
        return None


def extract_predicted_names(parts_demand: Optional[Dict[str, Any]]) -> set:
    """Normalised name set from p7_parts_demand items."""
    if not parts_demand:
        return set()
    return {
        str(i.get("name", "")).lower().strip()
        for i in parts_demand.get("items", [])
        if i.get("name")
    }


def extract_actual_names(parts_replaced_text: Optional[str]) -> set:
    """
    Parse OrdresIntervention.parts_replaced free text into a name set.
    Format: comma-separated items, may have (réf. XXX-NNN) suffix.
    """
    if not parts_replaced_text:
        return set()
    import re

    REF_PAT = re.compile(r"\(r[eé]f\.\s*[A-Z0-9\-]+\)", re.IGNORECASE)
    SPEC_PAT = re.compile(
        r"(?:⌀[\d\.]+\w*|\bx\d+\b|\b\d+[\w\-\.×/²³°%]*"
        r"|\b[A-Z]{2,6}[-/]?\d+[\w\-\.]*\b)",
        re.IGNORECASE,
    )
    names = set()
    for part in parts_replaced_text.split(","):
        s = REF_PAT.sub("", part)
        s = SPEC_PAT.sub(" ", s)
        s = " ".join(s.split()).strip().rstrip(",").lower()
        if s:
            names.add(s)
    return names


def compute_feedback_metrics(
    predicted_names: set,
    actual_names: set,
) -> Dict[str, Any]:
    """
    Precision: of predicted parts, how many were actually used?
    Recall:    of actually used parts, how many did we predict?
    Returns metrics dict logged to ml_prediction_log or feedback store.
    """
    if not predicted_names and not actual_names:
        return {
            "precision": None,
            "recall": None,
            "f1": None,
            "predicted_count": 0,
            "actual_count": 0,
            "tp": 0,
        }

    tp = len(predicted_names & actual_names)
    precision = round(tp / len(predicted_names), 4) if predicted_names else None
    recall = round(tp / len(actual_names), 4) if actual_names else None

    if precision is not None and recall is not None and (precision + recall) > 0:
        f1 = round(2 * precision * recall / (precision + recall), 4)
    else:
        f1 = None

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "predicted_count": len(predicted_names),
        "actual_count": len(actual_names),
    }


# ── Async DB operations ───────────────────────────────────────────────────


async def record_p7_feedback(
    intervention_id: int,
    db: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    For a completed intervention:
    1. Load parts_replaced text from OrdresIntervention.
    2. Find latest p7_parts_demand from ml_prediction_logs for that machine.
    3. Compare predicted vs actual, compute metrics.
    4. Mark intervention for P7 retrain queue via `retrained` flag logic.
    Returns feedback metrics dict or None if data insufficient.
    """
    from models.ordres_intervention import OrdresIntervention
    from models.ml_prediction_log import MlPredictionLog

    # 1. Load intervention
    itv_q = await db.execute(
        select(OrdresIntervention).where(OrdresIntervention.id == intervention_id)
    )
    itv = itv_q.scalar_one_or_none()
    # Use legacy_parts_text (direct text column) — parts_replaced is a computed
    # property that requires loaded consumed_items relationship (noload).
    parts_text = itv.legacy_parts_text if itv else None
    if not itv or not parts_text:
        logger.debug(
            f"[P7-feedback] Intervention {intervention_id}: no parts text data"
        )
        return None

    # 2. Find latest prediction log with p7_parts_demand for this machine
    pred_q = await db.execute(
        select(MlPredictionLog)
        .where(
            and_(
                MlPredictionLog.machine_id == itv.machine_id,
                MlPredictionLog.p7_parts_demand.is_not(None),
            )
        )
        .order_by(desc(MlPredictionLog.created_at))
        .limit(1)
    )
    pred_log = pred_q.scalar_one_or_none()
    if not pred_log:
        logger.debug(
            f"[P7-feedback] No p7_parts_demand log for machine {itv.machine_id}"
        )
        return None

    # 3. Compare
    parts_demand = parse_parts_demand_json(pred_log.p7_parts_demand)
    predicted = extract_predicted_names(parts_demand)
    actual = extract_actual_names(parts_text)
    metrics = compute_feedback_metrics(predicted, actual)

    metrics["intervention_id"] = intervention_id
    metrics["machine_id"] = itv.machine_id
    metrics["log_id"] = pred_log.id

    # 4. Queue for P7 retrain: reuse existing retrained=False pattern
    #    Intervention stays retrained=False → next ml_retraining pass picks it up.
    #    We log the feedback in the prediction_log row's p7_parts_demand field
    #    as an augmented JSON with a 'feedback' key (non-destructive update).
    try:
        augmented = dict(parts_demand or {})
        augmented["_feedback"] = {
            "intervention_id": intervention_id,
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1": metrics["f1"],
            "actual_count": metrics["actual_count"],
            # tp/predicted_count: needed (alongside actual_count above) to
            # micro-average precision/recall correctly across interventions
            # in the aggregation report — a mean of per-intervention ratios
            # would over-weight interventions with tiny predicted/actual sets.
            "tp": metrics["tp"],
            "predicted_count": metrics["predicted_count"],
        }
        pred_log.p7_parts_demand = json.dumps(augmented, default=str)
        await db.commit()
    except Exception as e:
        logger.warning(f"[P7-feedback] Failed to update prediction log: {e}")
        await db.rollback()

    logger.info(
        f"[P7-feedback] machine={itv.machine_id} itv={intervention_id} "
        f"P={metrics['precision']} R={metrics['recall']} F1={metrics['f1']}"
    )
    return metrics
