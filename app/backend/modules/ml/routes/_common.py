"""Shared constants and helpers used across the ml router split.

Not a route module itself — no APIRouter here.
"""
from datetime import timedelta
from pathlib import Path as _Path
import os

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.machine_telemetry import MachineTelemetry
from models.utilisateurs import Utilisateurs

# System/simulation entries need a non-null technician_id.
# Set SYSTEM_TECHNICIAN_ID env var to a valid technician PK in your DB.
# Default 0 works when there is no FK constraint on technician_id.
_SYSTEM_TECHNICIAN_ID = int(os.getenv("SYSTEM_TECHNICIAN_ID", "0"))

_BACKEND_MODELS = str(_Path(__file__).resolve().parents[1] / "models")
_MICRO_MODELS = str(_Path(__file__).resolve().parents[4] / "ml-microservice" / "models")

_MACHINE_NOT_FOUND_MSG = "Machine non trouvée"
_INVALID_HORIZON_MSG = "horizon must be 7, 30 or 60"
_VALID_HORIZONS = {7, 30, 60}


def _entries_to_log_dicts(machine_id: int, entries) -> list:
    """Pure conversion, no DB access — reusable when entries were batch-prefetched
    (e.g. fleet dashboard, which can't issue a query per asyncio.gather task since
    AsyncSession isn't safe for concurrent use on the same session)."""
    return [
        {
            "machine_id": machine_id,
            "air_temperature": e.air_temperature,
            "process_temperature": e.process_temperature,
            "rotational_speed": e.rotational_speed,
            "torque": e.torque,
            "tool_wear": e.tool_wear,
            "created_at": e.recorded_at.isoformat() if e.recorded_at else "",
            "risk_level": "LOW",
        }
        for e in entries
    ]


async def _get_telemetry_history(machine_id: int, db: AsyncSession):
    """
    Query all telemetry entries for a machine ordered oldest-first.
    Returns (entries, log_dicts) where log_dicts is compatible with
    FeatureStore.build_time_series_from_logs.

    Synthetic (seeded) rows are excluded unless
    settings.ml_allow_synthetic_telemetry is on (development only).
    """
    filters = [MachineTelemetry.machine_id == machine_id]
    if not settings.ml_allow_synthetic_telemetry:
        filters.append(MachineTelemetry.is_synthetic.is_(False))

    # Fetch latest 500 entries (matches microservice _MAX_LOGS cap).
    # Order DESC + limit, then reverse in Python to get oldest-first ascending.
    result = await db.execute(
        select(MachineTelemetry)
        .where(*filters)
        .order_by(MachineTelemetry.recorded_at.desc())
        .limit(500)
    )
    entries = list(reversed(result.scalars().all()))
    return entries, _entries_to_log_dicts(machine_id, entries)


def _latest_sensors(entries) -> tuple:
    """
    Return (air, process, rpm, torque, wear) from the newest telemetry entry,
    or all-None when the machine has no usable telemetry.

    Deliberately no placeholder defaults: a machine with no sensor history must
    surface as "no data", not as a plausible-looking reading.
    """
    if not entries:
        return (None, None, None, None, None)
    latest = entries[-1]
    return (
        float(latest.air_temperature),
        float(latest.process_temperature),
        int(latest.rotational_speed),
        float(latest.torque),
        float(latest.tool_wear),
    )


def _count_recent_interventions(interventions, cutoff) -> int:
    """Return count of interventions whose date_intervention is after cutoff."""
    count = 0
    for i in interventions:
        if not i.date_intervention:
            continue
        dt = (
            i.date_intervention.replace(tzinfo=cutoff.tzinfo)
            if i.date_intervention.tzinfo is None
            else i.date_intervention
        )
        if dt > cutoff:
            count += 1
    return count


def _require_admin(current_user: Utilisateurs):
    if not current_user.role or current_user.role.value != "ADMIN":
        raise HTTPException(status_code=403, detail="ADMIN role required.")


def _require_planner(current_user: Utilisateurs) -> None:
    """Allow CHEFTECH or ADMIN only."""
    if not current_user.role or current_user.role.value not in ("CHEFTECH", "ADMIN"):
        raise HTTPException(status_code=403, detail="Accès réservé aux planificateurs.")


__all__ = [
    "timedelta",
    "_SYSTEM_TECHNICIAN_ID",
    "_BACKEND_MODELS",
    "_MICRO_MODELS",
    "_MACHINE_NOT_FOUND_MSG",
    "_INVALID_HORIZON_MSG",
    "_VALID_HORIZONS",
    "_get_telemetry_history",
    "_entries_to_log_dicts",
    "_latest_sensors",
    "_count_recent_interventions",
    "_require_admin",
    "_require_planner",
]
