"""Retraining control, service status, model metrics/health (ADMIN)."""
from datetime import datetime, timedelta, timezone
from typing import Annotated, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_db
from core.ml_client import get_model_metrics, is_ml_service_available
from models.ml_prediction_log import MlPredictionLog
from models.utilisateurs import Utilisateurs

from ..services.drift import SENSORS, compute_drift
from ..services.ml_retraining import RetrainingService
from ..services.model_registry import check_sync, scan_models
from ..services.retraining_advisor import recommend_retraining
from ._common import _BACKEND_MODELS, _MICRO_MODELS, _require_admin

router = APIRouter(tags=["Machine Learning"])


@router.get("/retrain/stats")
async def get_retraining_stats(db: Annotated[AsyncSession, Depends(get_db)]) -> Dict:
    """
    Get statistics on new ground truth data available for retraining.
    Used by the ML Admin Dashboard.
    """
    return await RetrainingService.get_retraining_stats(db)


@router.post(
    "/retrain",
    responses={
        500: {"description": "Internal Server Error"},
        403: {"description": "ADMIN role required."},
    },
)
async def trigger_retraining(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    """
    Manually trigger the PDCA Act Phase: automated retraining. ADMIN only.
    Accepts optional JSON body {"model_type": "all"}.
    """
    _require_admin(current_user)
    try:
        result = await RetrainingService.run_retraining_pipeline(db)
        return (
            result
            if result is not None
            else {"status": "success", "message": "Retraining pipeline completed."}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def ml_service_status():
    """
    Check ML container status.
    Returns whether the ML microservice is available.
    """
    available = await is_ml_service_available()
    return {
        "ml_service_available": available,
        "ml_service_url": "http://ml-service:8000",
        "fallback": "Local calculation" if not available else "ML Container",
    }


@router.get("/model/metrics")
async def get_ml_model_metrics():
    """
    Get trained model metrics (ROC-AUC, PR-AUC, F1).
    Returns the performance metrics of the P1 failure prediction model.
    """
    metrics = await get_model_metrics()
    if metrics.get("success"):
        return {
            "success": True,
            "model": "p1_failure",
            "metrics": metrics.get("metrics", {}),
        }
    return {"success": False, "error": "Could not retrieve model metrics"}


async def _drift_rows(db: AsyncSession, start, end):
    cols = [getattr(MlPredictionLog, s) for s in SENSORS]
    stmt = (
        select(*cols)
        .where(MlPredictionLog.created_at >= start, MlPredictionLog.created_at < end)
        .limit(2000)
    )
    res = await db.execute(stmt)
    return [dict(zip(SENSORS, row)) for row in res.all()]


@router.get("/model-health", responses={403: {"description": "ADMIN role required."}})
async def model_health(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
):
    _require_admin(current_user)
    models = scan_models(_BACKEND_MODELS, _MICRO_MODELS)
    divergences = check_sync(_BACKEND_MODELS, _MICRO_MODELS)
    now = datetime.now(timezone.utc)
    try:
        baseline = await _drift_rows(
            db, now - timedelta(days=60), now - timedelta(days=30)
        )
        recent = await _drift_rows(db, now - timedelta(days=14), now)
        drift = compute_drift(baseline, recent)
    except Exception:
        drift = {"verdict": "insufficient_data", "sensors": {}}
    try:
        metrics = await get_model_metrics()
    except Exception:
        metrics = {"success": False}
    try:
        stats = await RetrainingService.get_retraining_stats(db)
        ndp = int(stats.get("new_data_points", 0))
    except Exception:
        ndp = 0
    retrain = recommend_retraining(ndp, drift["verdict"])
    return {
        "models": models,
        "divergences": divergences,
        "metrics": metrics,
        "drift": drift,
        "retrain": retrain,
    }
