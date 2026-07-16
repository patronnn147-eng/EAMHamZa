"""
Post-Maintenance Recovery Service.

Tracks how a machine's health evolves after a work order is completed.
Uses the same P1-P6 + DST fusion models as the rest of the ML pipeline —
no new models are trained; the unified_health_score is the single signal.

Flow:
    1. WO created -> snapshot_health() -> stored in OrdresTravail.health_score_at_creation
    2. WO completed -> snapshot_health() -> stored in OrdresTravail.health_score_at_completion
    3. Frontend reads recovery delta = current_unified_health_score - health_score_at_creation
"""

import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.ml_client import ml_client, is_ml_service_available
from models.machine_telemetry import MachineTelemetry
from models.OrdresTravail import OrdresTravail, OrdreStatut

logger = logging.getLogger(__name__)


# ── Tunables ───────────────────────────────────────────────────────────────
# unified_health_score must be >= this AND delta must be positive to call it Recovered.
RECOVERY_HEALTHY_THRESHOLD: float = 75.0

# Days after WO completion during which recovery is actively monitored / badged.
RECOVERY_WINDOW_DAYS: int = 7


@dataclass
class RecoveryResult:
    """Recovery snapshot for a single (machine, work_order) pair."""

    work_order_id: Optional[int]
    delta: Optional[float]  # current_score - health_score_at_creation
    status: str  # Recovered | Recovering | No improvement | Monitoring | No baseline
    score_before: Optional[float]  # health_score_at_creation
    score_after_completion: Optional[float]  # health_score_at_completion
    current_score: Optional[float]  # live unified_health_score
    days_since_completion: Optional[int]
    within_recovery_window: bool
    completion_date: Optional[str]  # ISO-8601

    def to_dict(self) -> Dict:
        return asdict(self)


class PostMaintenanceRecoveryService:
    """Computes pre/post health snapshots and recovery classification."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ─────────────────────────── snapshot ────────────────────────────────

    async def snapshot_health(self, machine_id: int) -> Optional[float]:
        """
        Get the current unified_health_score for a machine.

        Fetches latest telemetry and calls the existing ml_client.predict_all
        (same DST fusion used everywhere else). Never raises — returns None
        if the ML service is down or telemetry is missing, so the caller can
        proceed without blocking the WO transaction.
        """
        try:
            if not await is_ml_service_available():
                return None

            # Latest telemetry reading; default sensible operating values if none.
            result = await self.db.execute(
                select(MachineTelemetry)
                .where(MachineTelemetry.machine_id == machine_id)
                .order_by(MachineTelemetry.recorded_at.desc())
                .limit(1)
            )
            latest = result.scalar_one_or_none()
            if latest is not None:
                air, proc, rpm, torq, wear = (
                    float(latest.air_temperature),
                    float(latest.process_temperature),
                    int(latest.rotational_speed),
                    float(latest.torque),
                    int(float(latest.tool_wear)),
                )
            else:
                air, proc, rpm, torq, wear = 300.0, 310.0, 1500, 40.0, 0

            # History window for DST fusion (Kalman, CUSUM need it).
            hist_result = await self.db.execute(
                select(MachineTelemetry)
                .where(MachineTelemetry.machine_id == machine_id)
                .order_by(MachineTelemetry.recorded_at.desc())
                .limit(500)
            )
            telemetry_logs = [
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
                for e in reversed(hist_result.scalars().all())
            ]

            fusion = await ml_client.predict_all(
                air_temperature=air,
                process_temperature=proc,
                rotational_speed=rpm,
                torque=torq,
                tool_wear=wear,
                machine_id=machine_id,
                telemetry_logs=telemetry_logs,
                include_shap=False,
            )

            if not isinstance(fusion, dict):
                return None

            score = fusion.get("unified_health_score")
            if score is None:
                # Fallback: derive from P1 failure probability.
                p1 = fusion.get("p1_failure_probability")
                if p1 is None:
                    return None
                score = 100.0 - float(p1)

            return round(float(score), 2)

        except Exception as exc:
            logger.warning("snapshot_health failed for machine %s: %s", machine_id, exc)
            return None

    # ─────────────────────────── compute ─────────────────────────────────

    def compute_recovery(
        self,
        work_order: OrdresTravail,
        current_score: Optional[float],
    ) -> RecoveryResult:
        """Classify recovery state for a (work_order, current_score) pair."""
        before = (
            float(work_order.health_score_at_creation)
            if work_order.health_score_at_creation is not None
            else None
        )
        after_completion = (
            float(work_order.health_score_at_completion)
            if work_order.health_score_at_completion is not None
            else None
        )

        completion_date_iso: Optional[str] = (
            work_order.date_fin.isoformat() if work_order.date_fin else None
        )

        # Days since completion + window flag
        days_since: Optional[int] = None
        within_window = False
        if work_order.date_fin:
            dt = work_order.date_fin
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            days_since = (datetime.now(timezone.utc) - dt).days
            within_window = days_since <= RECOVERY_WINDOW_DAYS

        # Delta calculation
        delta: Optional[float] = None
        if before is not None and current_score is not None:
            delta = round(float(current_score) - before, 2)

        # Status classification
        completed = work_order.statut in (
            OrdreStatut.COMPLETED,
            OrdreStatut.VALIDATED,
            OrdreStatut.CLOSED,
        )

        if not completed:
            status = "Monitoring"
        elif before is None:
            status = "No baseline"
        elif delta is None:
            status = "No baseline"
        elif delta <= 0:
            status = "No improvement"
        elif current_score is not None and current_score >= RECOVERY_HEALTHY_THRESHOLD:
            status = "Recovered"
        else:
            status = "Recovering"

        return RecoveryResult(
            work_order_id=work_order.id,
            delta=delta,
            status=status,
            score_before=before,
            score_after_completion=after_completion,
            current_score=(
                round(float(current_score), 2) if current_score is not None else None
            ),
            days_since_completion=days_since,
            within_recovery_window=within_window,
            completion_date=completion_date_iso,
        )

    # ─────────────────────────── lookup ──────────────────────────────────

    async def get_latest_recovery_for_machine(
        self,
        machine_id: int,
        current_score: Optional[float],
    ) -> Optional[RecoveryResult]:
        """
        Most recently completed WO for this machine within the recovery window.
        Returns None if no qualifying WO exists.
        """
        result = await self.db.execute(
            select(OrdresTravail)
            .where(
                OrdresTravail.machine_id == machine_id,
                OrdresTravail.date_fin.isnot(None),
            )
            .order_by(OrdresTravail.date_fin.desc())
            .limit(1)
        )
        wo = result.scalar_one_or_none()
        if wo is None:
            return None

        recovery = self.compute_recovery(wo, current_score)
        # Suppress if completion is far in the past AND no baseline exists.
        if not recovery.within_recovery_window and recovery.score_before is None:
            return None
        return recovery
