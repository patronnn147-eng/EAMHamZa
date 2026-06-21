"""
ML snapshot for chat context injection.

Fetches the unified-health prediction for a machine and trims it to a lean
dict consumed by build_ml_context() in services/ai_prompts.py.

Returns None on ANY failure so the chat pipeline degrades gracefully to
RAG-only context — ML being down must never break a chat response.
"""

import logging
from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def get_ml_snapshot(machine_id: int, db: AsyncSession) -> Optional[Dict]:
    """
    Fetch live ML predictions for a machine, trimmed for chat prompt injection.

    Reuses the unified-health route function directly — single source of truth,
    same fields the frontend ML Intelligence tab displays.

    Never raises. Returns None when the machine is unknown, telemetry is
    missing, or the ML service is unavailable.
    """
    try:
        # Function-level import — avoids circular import (router imports
        # from modules.ml.services elsewhere).
        from modules.ml.router import get_unified_health

        raw = await get_unified_health(machine_id, db)

        # Machine type drives sensor threshold selection in build_ml_context
        machine_type = ""
        try:
            from models.machines import Machines

            res = await db.execute(
                select(Machines.type).where(Machines.id == machine_id)
            )
            machine_type = res.scalar_one_or_none() or ""
        except Exception:
            pass

        parts_demand = raw.get("parts_demand") or {}
        parts_items = (
            parts_demand.get("items") if isinstance(parts_demand, dict) else None
        )

        return {
            "machine_name": raw.get("machine_name", ""),
            "machine_type": machine_type,
            "health_score": raw.get("unified_health_score"),
            "dst_verdict": raw.get("dst_verdict"),
            "failure_probability": raw.get("failure_probability"),
            "risk_level": raw.get("risk_level"),
            "rul_days": raw.get("rul_days"),
            "is_anomaly": raw.get("is_anomaly", False),
            "p4_anomaly_score": raw.get("p4_anomaly_score", 0.0),
            "predicted_priority": raw.get("predicted_priority"),
            "p6_schedule_days": raw.get("p6_schedule_days"),
            "parts_items": parts_items or [],
            "parts_readiness": (raw.get("parts_readiness") or {}).get("status"),
            # Latest sensor readings
            "air_temperature": raw.get("air_temperature"),
            "process_temperature": raw.get("process_temperature"),
            "rotational_speed": raw.get("rotational_speed"),
            "torque": raw.get("torque"),
            "tool_wear": raw.get("tool_wear"),
        }

    except Exception as e:
        logger.warning(
            f"[chat_context] ML snapshot failed for machine {machine_id}: {e}"
        )
        return None
