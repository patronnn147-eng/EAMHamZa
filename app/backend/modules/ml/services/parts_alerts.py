"""
P7 Parts Shortage Alert Service.
Emits PARTS_SHORTAGE alerts when parts_demand reveals shortfalls.
Dedup is handled by AlertService.create_alert (one active per machine+type).
"""

import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from models.alertes import AlertType, AlertSeverity

logger = logging.getLogger(__name__)


def _build_shortage_message(items_with_shortfall: list) -> str:
    """Plain-language message listing parts with shortfall (no ML jargon)."""
    if not items_with_shortfall:
        return "Parts shortage detected."
    top = items_with_shortfall[:3]
    names = ", ".join(
        i.get("name", f"Part {i.get('piece_id', '?')}").title() for i in top
    )
    extra = len(items_with_shortfall) - len(top)
    suffix = f" (+{extra} more)" if extra > 0 else ""
    return f"Parts needed in the next 30 days — order: {names}{suffix}."


def _determine_severity(items_with_shortfall: list) -> AlertSeverity:
    """
    CRITICAL if any condition-based shortfall (machine about to fail, part missing).
    HIGH if consumption-based shortfall only.
    """
    for item in items_with_shortfall:
        if item.get("driver") == "condition":
            return AlertSeverity.CRITICAL
    return AlertSeverity.HIGH


def extract_shortage_items(parts_demand: Optional[Dict[str, Any]]) -> list:
    """
    Return items with shortfall > 0 from a parts_demand contract.
    Pure function — no DB, fully testable.
    """
    if not parts_demand or not isinstance(parts_demand.get("items"), list):
        return []
    return [i for i in parts_demand["items"] if (i.get("shortfall") or 0) > 0]


async def emit_shortfall_alert(
    machine_id: int,
    parts_demand: Optional[Dict[str, Any]],
    db: AsyncSession,
) -> None:
    """
    Create (or reuse) a PARTS_SHORTAGE alert when parts_demand has shortfalls.
    Silently no-ops when no shortfall or parts_demand is None.
    AlertService.create_alert already deduplicates: if an active PARTS_SHORTAGE
    alert exists for this machine it returns the existing one.
    """
    shortage_items = extract_shortage_items(parts_demand)
    if not shortage_items:
        return

    try:
        from services.alertes import AlertService  # local import avoids circular dep

        message = _build_shortage_message(shortage_items)
        severity = _determine_severity(shortage_items)

        await AlertService(db).create_alert(
            machine_id=machine_id,
            alert_type=AlertType.PARTS_SHORTAGE,
            severity=severity,
            message=message,
        )
        logger.info(
            f"[P7] PARTS_SHORTAGE alert emitted for machine {machine_id} "
            f"({len(shortage_items)} parts with shortfall)"
        )
    except Exception:
        # Non-fatal — alert failure must never break unified-health response
        logger.warning(
            f"[P7] Failed to emit PARTS_SHORTAGE alert for machine {machine_id}",
            exc_info=True,
        )
