from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from core.database import get_db
from models.machines import Machines
from models.ordres_intervention import Ordres_intervention
from models.ordres_travail import Ordres_travail
from models.ml_prediction_log import MlPredictionLog
from .predictions import MachineLearningService
from .rul_calculator import RULCalculator
from .services.ml_retraining import RetrainingService
from core.ml_client import ml_client, is_ml_service_available

from pydantic import BaseModel
from typing import Dict, List, Optional
from schemas.pagination import PaginatedResponse
from sqlalchemy import func
from datetime import datetime, timedelta
import asyncio

router = APIRouter(prefix="/api/v1/ml", tags=["Machine Learning"])

# Simple in-memory cache for fleet dashboard
_fleet_cache = {
    "data": None,
    "timestamp": None,
    "ttl_seconds": 300  # 5 minutes cache
}


class TelemetryUpdate(BaseModel):
    air_temperature: Optional[float] = None
    process_temperature: Optional[float] = None
    rotational_speed: Optional[int] = None
    torque: Optional[float] = None
    tool_wear: Optional[int] = None



@router.get("/machines/{machine_id}/prediction")
async def get_machine_prediction(machine_id: int, db: AsyncSession = Depends(get_db)) -> Dict:
    """
    Get ML-based predictive maintenance data for a specific machine.
    Uses intervention history + the trained .pkl model to estimate:
      - rul_days: estimated days before failure
      - risk_level: LOW / MEDIUM / HIGH / CRITICAL
      - failure_probability: 0-100 (blended from model + MTBF)
      - predicted_failure_date: ISO timestamp
    Also logs the prediction to ml_prediction_logs (PDCA Shadow Logging).
    """
    # 1. Fetch machine
    result = await db.execute(select(Machines).where(Machines.id == machine_id))
    machine = result.scalar_one_or_none()

    if not machine:
        raise HTTPException(status_code=404, detail="Machine non trouvée")

    # 2. Fetch intervention history for this machine
    interventions_query = select(Ordres_intervention).where(
        Ordres_intervention.machine_id == machine_id
    )
    execute_result = await db.execute(interventions_query)
    interventions = list(execute_result.scalars().all())

    # 3. Fetch count of open work orders (Ordres de travail)
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import func
    now_dt = datetime.now(timezone.utc)
    
    # Open = not TERMINÉ or ANNULÉ
    wo_query = select(func.count(Ordres_travail.id)).where(
        Ordres_travail.machine_id == machine_id,
        ~Ordres_travail.statut.in_(["TERMINÉ", "ANNULÉ"])
    )
    wo_result = await db.execute(wo_query)
    open_wo_count = wo_result.scalar() or 0

    # 4. Count recent interventions (last 30 days)
    thirty_days_ago = now_dt - timedelta(days=30)
    recent_interventions_count = len([
        i for i in interventions 
        if i.date_intervention and (
            i.date_intervention.replace(tzinfo=timezone.utc) if i.date_intervention.tzinfo is None else i.date_intervention
        ) > thirty_days_ago
    ])

    # 5. Calculate prediction with unified health
    try:
        prediction = RULCalculator.calculate_rul(
            machine, 
            interventions,
            open_work_orders=open_wo_count,
            recent_interventions=recent_interventions_count
        )

        # 4. Shadow Log (PDCA Phase 1): persist prediction without showing to user
        try:
            log_entry = MachineLearningService.create_shadow_log(prediction)
            db.add(log_entry)
            await db.commit()
        except Exception:
            await db.rollback()  # Don't fail the prediction if logging fails

        return prediction
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"ML Calculation Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur lors du calcul ML: {str(e)}")


@router.get("/machines/{machine_id}/failure-probability")
async def get_failure_probability(
    machine_id: int,
    air: float = Query(..., description="Air temperature [K]"),
    process: float = Query(..., description="Process temperature [K]"),
    rpm: int = Query(..., description="Rotational speed [rpm]"),
    torque: float = Query(..., description="Torque [Nm]"),
    wear: int = Query(..., description="Tool wear [min]"),
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    Return failure probability for a machine using the trained ML model (P1).

    Feature order matches training data: [air, process, rpm, torque, wear]

    Returns:
        machine_id: int
        failure_probability: float (0–100)
        risk_level: "LOW_RISK" | "HIGH_RISK"
    """
    result = await db.execute(select(Machines).where(Machines.id == machine_id))
    machine = result.scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine non trouvée")

    features = [air, process, float(rpm), torque, float(wear)]
    probability = MachineLearningService.predict_failure_probability(features)

    return {
        "machine_id": machine_id,
        "machine_name": machine.nom,
        "failure_probability": probability,
        "risk_level": "HIGH_RISK" if probability > 50 else "LOW_RISK",
    }


@router.get("/machines/{machine_id}/failure-type")
async def get_failure_type(
    machine_id: int,
    air: float = Query(..., description="Air temperature [K]"),
    process: float = Query(..., description="Process temperature [K]"),
    rpm: int = Query(..., description="Rotational speed [rpm]"),
    torque: float = Query(..., description="Torque [Nm]"),
    wear: int = Query(..., description="Tool wear [min]"),
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    Predict specific failure types for a machine (P2).
    Returns binary detection and probability for each type:
    TWF, HDF, PWF, OSF, RNF
    """
    result = await db.execute(select(Machines).where(Machines.id == machine_id))
    machine = result.scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine non trouvée")

    # Features: [air, process, rpm, torque, wear, temp_delta]
    temp_delta = process - air
    features = [float(air), float(process), float(rpm), float(torque), float(wear), float(temp_delta)]

    failure_types = MachineLearningService.predict_failure_type(features)

    return {
        "machine_id": machine_id,
        "machine_name": machine.nom,
        "failure_types": failure_types
    }


@router.get("/fleet/critical")
async def get_fleet_critical_predictions(db: AsyncSession = Depends(get_db)):
    """
    Get machines with the highest risk of failure across the fleet.
    Returns only HIGH and CRITICAL risk machines, sorted by rul_days ascending.
    """
    result = await db.execute(select(Machines))
    machines = result.scalars().all()
    predictions = []

    for machine in machines:
        interventions_query = select(Ordres_intervention).where(
            Ordres_intervention.machine_id == machine.id
        )
        execute_result = await db.execute(interventions_query)
        interventions = execute_result.scalars().all()

        pred = RULCalculator.calculate_rul(machine, list(interventions))
        if pred["risk_level"] in ["CRITICAL", "HIGH"]:
            predictions.append(pred)

    return {"machines": sorted(predictions, key=lambda x: x["rul_days"])}


async def _process_single_machine(machine: Machines, db: AsyncSession) -> Dict:
    """Helper to process single machine prediction."""
    interventions_query = select(Ordres_intervention).where(
        Ordres_intervention.machine_id == machine.id
    )
    execute_result = await db.execute(interventions_query)
    interventions = execute_result.scalars().all()
    
    pred = RULCalculator.calculate_rul(machine, list(interventions))
    pred["zone"] = machine.zone
    pred["sous_zone"] = machine.sous_zone
    pred["statut"] = machine.statut
    return pred


@router.get("/fleet/dashboard")
async def get_fleet_dashboard(db: AsyncSession = Depends(get_db)):
    """
    PDCA Fleet Dashboard: Full overview of ALL machines with ML predictions.
    Cached for 5 minutes + parallel processing for speed.
    """
    now = datetime.utcnow()
    
    # Check cache
    if (_fleet_cache["data"] is not None and 
        _fleet_cache["timestamp"] is not None and
        (now - _fleet_cache["timestamp"]).total_seconds() < _fleet_cache["ttl_seconds"]):
        return _fleet_cache["data"]
    
    # Build dashboard fresh - parallel processing
    result = await db.execute(select(Machines))
    machines = result.scalars().all()

    # Process all machines in parallel
    tasks = [_process_single_machine(m, db) for m in machines]
    dashboard = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out errors
    dashboard = [d for d in dashboard if isinstance(d, dict)]

    # Sort: CRITICAL first, then HIGH, then MEDIUM, then LOW
    risk_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    sorted_dashboard = sorted(dashboard, key=lambda x: (risk_order.get(x["risk_level"], 4), x["rul_days"]))
    
    # Cache result
    _fleet_cache["data"] = sorted_dashboard
    _fleet_cache["timestamp"] = now
    
    return sorted_dashboard


@router.post("/fleet/dashboard/refresh")
async def refresh_fleet_dashboard():
    """Force refresh the fleet dashboard cache."""
    _fleet_cache["data"] = None
    _fleet_cache["timestamp"] = None
    return {"status": "cache_cleared", "message": "Dashboard cache cleared. Next request will rebuild."}


@router.get("/shadow-logs")
async def get_shadow_logs(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(100, ge=1, le=1000, description="Items per page"),
    machine_id: int = Query(None, description="Filter by machine ID"),
    risk_level: str = Query(None, description="Filter by risk level (CRITICAL, HIGH, MEDIUM, LOW)"),
    db: AsyncSession = Depends(get_db),
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

    return PaginatedResponse.create(items=items, total=total_count, page=page, size=size)


@router.patch("/machines/{machine_id}/telemetry")
async def update_machine_telemetry(
    machine_id: int,
    data: TelemetryUpdate,
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    Update machine telemetry sensor values (Simulation).
    Used to test ML predictions by manually setting data.
    """
    result = await db.execute(select(Machines).where(Machines.id == machine_id))
    machine = result.scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine non trouvée")

    if data.air_temperature is not None:
        machine.air_temperature = data.air_temperature
    if data.process_temperature is not None:
        machine.process_temperature = data.process_temperature
    if data.rotational_speed is not None:
        machine.rotational_speed = data.rotational_speed
    if data.torque is not None:
        machine.torque = data.torque
    if data.tool_wear is not None:
        machine.tool_wear = data.tool_wear

    await db.commit()
    await db.refresh(machine)

    return {
        "message": "Telemetry updated successfully",
        "machine_id": machine_id,
        "telemetry": {
            "air_temperature": machine.air_temperature,
            "process_temperature": machine.process_temperature,
            "rotational_speed": machine.rotational_speed,
            "torque": machine.torque,
            "tool_wear": machine.tool_wear,
        },
    }


@router.get("/retrain/stats")
async def get_retraining_stats(db: AsyncSession = Depends(get_db)) -> Dict:
    """
    Get statistics on new ground truth data available for retraining.
    Used by the ML Admin Dashboard.
    """
    return await RetrainingService.get_retraining_stats(db)


@router.post("/retrain")
async def trigger_retraining(db: AsyncSession = Depends(get_db)):
    """
    Manually trigger the PDCA Act Phase: automated retraining.
    """
    try:
        await RetrainingService.run_retraining_pipeline(db)
        return {"status": "success", "message": "Retraining pipeline completed."}
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
        "fallback": "Local calculation" if not available else "ML Container"
    }
