"""Per-machine ML prediction endpoints: RUL, failure probability, failure type."""
from datetime import datetime, timedelta, timezone
from typing import Annotated, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.ml_client import is_ml_service_available, ml_client
from models.machines import Machines
from models.ordres_intervention import OrdresIntervention
from models.ordres_travail import OrdresTravail

from ..logging import ShadowLogger
from ..rul_calculator import RULCalculator
from ._common import _MACHINE_NOT_FOUND_MSG, _get_telemetry_history, _latest_sensors

router = APIRouter(tags=["Machine Learning"])


@router.get("/machines/{machine_id}/prediction", responses={404: {"description": "Machine non trouvée"}, 500: {"description": "Internal Server Error"}})
async def get_machine_prediction(
    machine_id: int, db: Annotated[AsyncSession, Depends(get_db)]
) -> Dict:
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
        raise HTTPException(status_code=404, detail=_MACHINE_NOT_FOUND_MSG)

    # 2. Fetch intervention history for this machine
    interventions_query = select(OrdresIntervention).where(
        OrdresIntervention.machine_id == machine_id
    )
    execute_result = await db.execute(interventions_query)
    interventions = list(execute_result.scalars().all())

    # 3. Fetch count of open work orders (Ordres de travail)
    now_dt = datetime.now(timezone.utc)

    # A work order counts as open when its status is neither TERMINÉ nor ANNULÉ.
    wo_query = select(func.count(OrdresTravail.id)).where(
        OrdresTravail.machine_id == machine_id,
        cast(OrdresTravail.statut, String).notin_(
            ["CLOSED", "VALIDATED", "REJECTED", "ANNULÉ"]
        ),
    )
    wo_result = await db.execute(wo_query)
    open_wo_count = wo_result.scalar() or 0

    # 4. Count recent interventions (last 30 days)
    thirty_days_ago = now_dt - timedelta(days=30)
    recent_interventions_count = len(
        [
            i
            for i in interventions
            if i.date_intervention
            and (
                i.date_intervention.replace(tzinfo=timezone.utc)
                if i.date_intervention.tzinfo is None
                else i.date_intervention
            )
            > thirty_days_ago
        ]
    )

    # 5. Query telemetry history; derive scalars from latest entry or use defaults
    telemetry_entries, telemetry_logs = await _get_telemetry_history(machine_id, db)

    # No telemetry => all-None sensors (never placeholder readings, see
    # _latest_sensors) and no ML call: the models would only echo the
    # placeholders back identically for every machine.
    _air, _proc, _rpm, _torq, _wear = _latest_sensors(telemetry_entries)

    # 6. Optionally fetch DST fusion from ML microservice (best-effort, non-blocking)
    fusion_result: Optional[Dict] = None
    try:
        if telemetry_entries and await is_ml_service_available():
            fusion_result = await ml_client.predict_all(
                air_temperature=_air,
                process_temperature=_proc,
                rotational_speed=_rpm,
                torque=_torq,
                tool_wear=int(_wear),
                machine_id=machine_id,
                telemetry_logs=telemetry_logs,
            )
    except Exception:
        pass  # ML microservice unavailable — rul_calculator uses fallback formula

    # 7. Calculate prediction with unified health
    try:
        prediction = RULCalculator.calculate_rul(
            machine,
            interventions,
            telemetry_entries=telemetry_entries,
            open_work_orders=open_wo_count,
            recent_interventions=recent_interventions_count,
            fusion_result=fusion_result,
        )

        # 4. Shadow Log (PDCA Phase 1): persist prediction without showing to user
        try:
            log_entry = ShadowLogger.create_shadow_log(prediction)
            db.add(log_entry)
            await db.commit()
        except Exception:
            await db.rollback()  # Don't fail the prediction if logging fails

        return prediction
    except Exception as e:
        import logging

        logging.getLogger(__name__).exception(f"ML Calculation Error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Erreur lors du calcul ML: {str(e)}"
        )


@router.get("/machines/{machine_id}/failure-probability", responses={404: {"description": "Machine non trouvée"}})
async def get_failure_probability(
    machine_id: int,
    air: Annotated[float, Query(description="Air temperature [K]")],
    process: Annotated[float, Query(description="Process temperature [K]")],
    rpm: Annotated[int, Query(description="Rotational speed [rpm]")],
    torque: Annotated[float, Query(description="Torque [Nm]")],
    wear: Annotated[int, Query(description="Tool wear [min]")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Dict:
    """
    Return failure probability for a machine using the trained ML model (P1).

    Feature order matches training data: [air, process, rpm, torque, wear]

    Returns:
        machine_id: int
        failure_probability: float (0-100)
        risk_level: "LOW_RISK" | "HIGH_RISK"
    """
    result = await db.execute(select(Machines).where(Machines.id == machine_id))
    machine = result.scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail=_MACHINE_NOT_FOUND_MSG)

    # Delegate to ML microservice
    try:
        ml_result = await ml_client.predict_failure_probability(
            air_temperature=air,
            process_temperature=process,
            rotational_speed=rpm,
            torque=torque,
            tool_wear=wear,
        )
        probability = float(
            ml_result.get(
                "failure_probability",
                ml_result.get("prediction", {}).get("failure_probability", 0.0),
            )
        )
    except Exception:
        probability = 0.0

    return {
        "machine_id": machine_id,
        "machine_name": machine.nom,
        "failure_probability": probability,
        "risk_level": "HIGH_RISK" if probability > 50 else "LOW_RISK",
    }


@router.get("/machines/{machine_id}/failure-type", responses={404: {"description": "Machine non trouvée"}})
async def get_failure_type(
    machine_id: int,
    air: Annotated[float, Query(description="Air temperature [K]")],
    process: Annotated[float, Query(description="Process temperature [K]")],
    rpm: Annotated[int, Query(description="Rotational speed [rpm]")],
    torque: Annotated[float, Query(description="Torque [Nm]")],
    wear: Annotated[int, Query(description="Tool wear [min]")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Dict:
    """
    Predict specific failure types for a machine (P2).
    Returns binary detection and probability for each type:
    TWF, HDF, PWF, OSF, RNF
    """
    result = await db.execute(select(Machines).where(Machines.id == machine_id))
    machine = result.scalar_one_or_none()
    if not machine:
        raise HTTPException(status_code=404, detail=_MACHINE_NOT_FOUND_MSG)

    # Delegate to ML microservice
    try:
        ml_result = await ml_client.predict_failure_type(
            air_temperature=air,
            process_temperature=process,
            rotational_speed=rpm,
            torque=torque,
            tool_wear=wear,
        )
        failure_types = ml_result.get("failure_types", {})
    except Exception:
        failure_types = {}

    return {
        "machine_id": machine_id,
        "machine_name": machine.nom,
        "failure_types": failure_types,
    }
