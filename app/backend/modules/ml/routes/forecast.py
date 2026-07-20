"""C8 forecasting: fleet downtime, labor demand, budget, schedule optimization."""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_db
from models.ordres_travail import OrdresTravail, OrdreStatut
from models.utilisateurs import Utilisateurs

from ._common import _INVALID_HORIZON_MSG, _VALID_HORIZONS, _require_planner

router = APIRouter(tags=["Machine Learning"])

_FORECAST_SUMMARY_CACHE: dict = {"data": None, "ts": None, "ttl": 1800}


async def _open_wo_count(db: AsyncSession) -> int:
    res = await db.execute(
        select(func.count())
        .select_from(OrdresTravail)
        .where(
            OrdresTravail.statut.in_(
                [OrdreStatut.APPROVED, OrdreStatut.ASSIGNED, OrdreStatut.IN_PROGRESS]
            )
        )
    )
    return res.scalar_one() or 0


async def _technician_count(db: AsyncSession) -> int:
    from models.utilisateurs import Utilisateurs as U

    res = await db.execute(select(func.count(U.id)).where(U.role == "TECHNICIEN"))
    return res.scalar_one()


@router.get("/forecast/summary")
async def get_forecast_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
) -> dict:
    """3 KPI cards for all roles — 30-day horizon, cached 30 min."""
    from ..services.downtime_forecast import compute_fleet_downtime
    from ..services.labor_forecast import forecast_labor
    from ..services.budget_forecast import forecast_budget
    from ..services.demand_forecast import compute_demand_forecast

    now = datetime.now(timezone.utc)
    if (
        _FORECAST_SUMMARY_CACHE["data"] is not None
        and _FORECAST_SUMMARY_CACHE["ts"] is not None
        and (now - _FORECAST_SUMMARY_CACHE["ts"]).total_seconds()
        < _FORECAST_SUMMARY_CACHE["ttl"]
    ):
        return _FORECAST_SUMMARY_CACHE["data"]

    downtime = await compute_fleet_downtime(db, horizon_days=30)
    tech_count = await _technician_count(db)
    open_wo_count = await _open_wo_count(db)

    labor = forecast_labor(
        machine_forecasts=downtime["machines"],
        open_wo_count=open_wo_count,
        avg_wo_hours=4.0,
        technician_count=tech_count,
        horizon_days=30,
    )

    demand_data = await compute_demand_forecast(db, horizon_days=60, limit=50)
    budget = forecast_budget(
        labor_demand_hours=labor["demand_hours"],
        parts_reorder_items=demand_data.get("items", []),
    )

    payload = {
        "downtime_hours": downtime["total_expected_hours"],
        "labor_demand_hours": labor["demand_hours"],
        "labor_overload": labor["overload"],
        "budget_total": budget["total"],
        "currency": "EUR",
        "horizon_days": 30,
        "generated_at": now.isoformat(),
    }
    _FORECAST_SUMMARY_CACHE["data"] = payload
    _FORECAST_SUMMARY_CACHE["ts"] = now
    return payload


@router.get("/forecast/downtime", responses={400: {"description": "horizon must be 7, 30 or 60"}, 403: {"description": "CHEFTECH or ADMIN role required."}})
async def get_forecast_downtime(
    *, horizon: Annotated[int, Query(description="7, 30 or 60")] = 30,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
) -> dict:
    """Per-machine downtime forecast. CHEFTECH + ADMIN only."""
    _require_planner(current_user)
    if horizon not in _VALID_HORIZONS:
        raise HTTPException(400, detail=_INVALID_HORIZON_MSG)
    from ..services.downtime_forecast import compute_fleet_downtime

    return await compute_fleet_downtime(db, horizon_days=horizon)


@router.get("/forecast/labor", responses={400: {"description": "horizon must be 7, 30 or 60"}, 403: {"description": "CHEFTECH or ADMIN role required."}})
async def get_forecast_labor(
    *, horizon: Annotated[int, Query(description="7, 30 or 60")] = 30,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
) -> dict:
    """Labor demand vs capacity. CHEFTECH + ADMIN only."""
    _require_planner(current_user)
    if horizon not in _VALID_HORIZONS:
        raise HTTPException(400, detail=_INVALID_HORIZON_MSG)
    from ..services.downtime_forecast import compute_fleet_downtime
    from ..services.labor_forecast import forecast_labor

    downtime = await compute_fleet_downtime(db, horizon_days=horizon)
    tech_count = await _technician_count(db)
    open_wo_count = await _open_wo_count(db)
    return forecast_labor(downtime["machines"], open_wo_count, 4.0, tech_count, horizon)


@router.get("/forecast/budget", responses={400: {"description": "horizon must be 7, 30 or 60"}, 403: {"description": "CHEFTECH or ADMIN role required."}})
async def get_forecast_budget(
    *, horizon: Annotated[int, Query(description="7, 30 or 60")] = 30,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
) -> dict:
    """Cost breakdown. CHEFTECH + ADMIN only."""
    _require_planner(current_user)
    if horizon not in _VALID_HORIZONS:
        raise HTTPException(400, detail=_INVALID_HORIZON_MSG)
    from ..services.downtime_forecast import compute_fleet_downtime
    from ..services.labor_forecast import forecast_labor
    from ..services.budget_forecast import forecast_budget
    from ..services.demand_forecast import compute_demand_forecast

    downtime = await compute_fleet_downtime(db, horizon_days=horizon)
    tech_count = await _technician_count(db)
    open_wo_count = await _open_wo_count(db)
    labor = forecast_labor(
        downtime["machines"], open_wo_count, 4.0, tech_count, horizon
    )
    demand_data = await compute_demand_forecast(db, horizon_days=horizon, limit=50)
    return forecast_budget(labor["demand_hours"], demand_data.get("items", []))


@router.post("/forecast/optimize-schedule", responses={400: {"description": "horizon must be 7, 30 or 60"}, 403: {"description": "CHEFTECH or ADMIN role required."}})
async def post_optimize_schedule(
    *, horizon: Annotated[int, Query(description="7, 30 or 60")] = 30,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
) -> dict:
    """Trigger OR-Tools schedule optimizer. CHEFTECH + ADMIN only. Cached 30 min."""
    _require_planner(current_user)
    if horizon not in _VALID_HORIZONS:
        raise HTTPException(400, detail=_INVALID_HORIZON_MSG)
    from ..services.schedule_optimizer import compute_schedule

    return await compute_schedule(db, horizon_days=horizon)


@router.get("/forecast/my-schedule")
async def get_my_schedule(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
) -> dict:
    """TECHNICIEN: returns their own assignments from the cached schedule."""
    from ..services.schedule_optimizer import compute_schedule

    schedule = await compute_schedule(db, horizon_days=30)
    my_assignments = [
        a
        for a in schedule.get("assignments", [])
        if a.get("technician_id") == current_user.id
    ]
    return {
        "assignments": my_assignments,
        "technician_id": current_user.id,
        "solved": schedule.get("solved"),
        "fallback": schedule.get("fallback"),
    }
