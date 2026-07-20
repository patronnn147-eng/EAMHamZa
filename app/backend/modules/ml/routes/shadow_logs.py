"""PDCA shadow-log audit trail, P4 anomaly-review adjudication, P7 feedback report."""
import json
from datetime import datetime, timezone
from typing import Annotated, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_db
from models.ml_prediction_log import MlPredictionLog
from models.utilisateurs import Utilisateurs
from schemas.pagination import PaginatedResponse

router = APIRouter(tags=["Machine Learning"])


@router.get("/shadow-logs")
async def get_shadow_logs(
    *, page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    size: Annotated[int, Query(ge=1, le=1000, description="Items per page")] = 100,
    machine_id: Annotated[int, Query(description="Filter by machine ID")] = None,
    risk_level: Annotated[str, Query(
        description="Filter by risk level (CRITICAL, HIGH, MEDIUM, LOW)"
    )] = None,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaginatedResponse[Dict]:
    """
    PDCA Audit: Retrieve shadow-logged ML predictions.
    Used by managers to compare predictions against actual outcomes.
    """
    query = select(MlPredictionLog)
    count_query = select(func.count()).select_from(MlPredictionLog)

    if machine_id is not None:
        query = query.where(MlPredictionLog.machine_id == machine_id)
        count_query = count_query.where(MlPredictionLog.machine_id == machine_id)
    if risk_level is not None:
        query = query.where(MlPredictionLog.risk_level == risk_level)
        count_query = count_query.where(MlPredictionLog.risk_level == risk_level)

    total_result = await db.execute(count_query)
    total_count = total_result.scalar_one()

    skip = (page - 1) * size
    query = query.order_by(desc(MlPredictionLog.created_at)).offset(skip).limit(size)

    # nosemgrep: python.fastapi.db.generic-sql-fastapi -- `query` is a SQLAlchemy
    # Core select() where machine_id/risk_level are bound via ORM == comparisons;
    # no raw SQL or string interpolation is involved.
    result = await db.execute(query)
    logs = result.scalars().all()

    items = [
        {
            "id": log.id,
            "machine_id": log.machine_id,
            "machine_name": log.machine_name,
            "risk_level": log.risk_level,
            "failure_probability": log.failure_probability,
            "rul_days": log.rul_days,
            "predicted_failure_date": log.predicted_failure_date,
            "predicted_priority": log.predicted_priority,
            "is_anomaly": log.is_anomaly,
            "anomaly_score": log.anomaly_score,
            "data_points": log.data_points,
            "ml_model_used": log.ml_model_used,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]

    return PaginatedResponse.create(
        items=items, total=total_count, page=page, size=size
    )


_ANOMALY_VERDICTS = {"CONFIRMED", "FALSE_POSITIVE", "BENIGN_TRANSIENT"}


class AnomalyVerdictData(BaseModel):
    verdict: str  # CONFIRMED / FALSE_POSITIVE / BENIGN_TRANSIENT
    root_cause_if_found: Optional[str] = None


@router.get("/anomaly-review/queue")
async def get_anomaly_review_queue(
    *, limit: Annotated[int, Query(ge=1, le=200, description="Max flags to return")] = 50,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Dict:
    """
    P4 evaluation loop: flagged anomalies awaiting technician adjudication.
    First-ever ground truth source for the unsupervised anomaly ensemble —
    without this, P4's precision/recall can never be measured.
    """
    query = (
        select(MlPredictionLog)
        .where(
            MlPredictionLog.is_anomaly.is_(True),
            MlPredictionLog.anomaly_verdict.is_(None),
            MlPredictionLog.is_synthetic.is_(False),
        )
        .order_by(desc(MlPredictionLog.created_at))
        .limit(limit)
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "pending_count": len(logs),
        "items": [
            {
                "id": log.id,
                "machine_id": log.machine_id,
                "machine_name": log.machine_name,
                "anomaly_score": log.anomaly_score,
                "sensor_snapshot": {
                    "air_temperature": log.air_temperature,
                    "process_temperature": log.process_temperature,
                    "rotational_speed": log.rotational_speed,
                    "torque": log.torque,
                    "tool_wear": log.tool_wear,
                },
                "flagged_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }


@router.patch("/anomaly-review/{log_id}", responses={404: {"description": "Prediction log not found"}, 400: {"description": "Invalid verdict"}})
async def submit_anomaly_verdict(
    log_id: int,
    data: AnomalyVerdictData,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
) -> Dict:
    """Technician adjudication of a P4 anomaly flag: was it real?"""
    if data.verdict not in _ANOMALY_VERDICTS:
        raise HTTPException(
            status_code=400,
            detail=f"verdict must be one of {sorted(_ANOMALY_VERDICTS)}",
        )

    result = await db.execute(select(MlPredictionLog).where(MlPredictionLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Prediction log not found")

    log.anomaly_verdict = data.verdict
    log.anomaly_root_cause = data.root_cause_if_found
    log.anomaly_reviewed_by = current_user.id if current_user else None
    log.anomaly_reviewed_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "id": log.id,
        "anomaly_verdict": log.anomaly_verdict,
        "anomaly_reviewed_at": log.anomaly_reviewed_at.isoformat(),
    }


@router.get("/p7-feedback/report")
async def get_p7_feedback_report(db: Annotated[AsyncSession, Depends(get_db)]) -> Dict:
    """
    Aggregates the predicted-vs-actual comparisons p7_feedback.py has been
    writing into ml_prediction_logs.p7_parts_demand._feedback on every
    completed intervention, into a live precision/recall report — replacing
    the stale 12%/100% figure from the original May training run, which has
    never been re-verified against real usage.

    Micro-averaged (sum of tp / sum of predicted, sum of tp / sum of actual)
    rather than a mean of per-intervention ratios, so interventions with a
    tiny predicted or actual parts set don't get equal weight to ones with
    many — a mean-of-ratios would be a common but misleading way to combine
    these. Older feedback entries recorded before tp/predicted_count were
    added to the log are skipped and counted separately rather than silently
    dropped from the denominator.
    """
    query = select(MlPredictionLog).where(MlPredictionLog.p7_parts_demand.like("%_feedback%"))
    result = await db.execute(query)
    logs = result.scalars().all()

    total_tp = total_predicted = total_actual = 0
    usable = 0
    skipped_legacy = 0
    per_intervention = []

    for log in logs:
        try:
            parsed = json.loads(log.p7_parts_demand or "{}")
        except Exception:
            continue
        fb = parsed.get("_feedback")
        if not fb:
            continue
        if fb.get("tp") is None or fb.get("predicted_count") is None:
            skipped_legacy += 1
            continue
        total_tp += fb["tp"]
        total_predicted += fb["predicted_count"]
        total_actual += fb.get("actual_count") or 0
        usable += 1
        per_intervention.append({
            "intervention_id": fb.get("intervention_id"),
            "machine_id": log.machine_id,
            "precision": fb.get("precision"),
            "recall": fb.get("recall"),
        })

    precision = round(total_tp / total_predicted, 4) if total_predicted else None
    recall = round(total_tp / total_actual, 4) if total_actual else None
    f1 = (
        round(2 * precision * recall / (precision + recall), 4)
        if precision is not None and recall is not None and (precision + recall) > 0
        else None
    )

    return {
        "sample_count": usable,
        "skipped_legacy_entries": skipped_legacy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "note": (
            "No feedback recorded yet — precision/recall will appear once "
            "technicians complete interventions with parts_replaced data."
            if usable == 0 else None
        ),
        "per_intervention": per_intervention[-20:],  # most recent slice, not the full history
    }
