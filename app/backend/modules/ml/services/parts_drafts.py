"""
P7.4 — Guarded draft creation for parts procurement.
Shortfall → DRAFT Ordres_travail (human must approve before anything commits).
Dedup: if PARTS_SHORTAGE alert already has a work_order_id, skip creation.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)


# ── Pure helpers (fully testable, no DB) ──────────────────────────────────


def _determine_priority(shortage_items: list) -> str:
    """
    URGENTE if condition-based shortfall (machine about to fail).
    ÉLEVÉE  if consumption-based shortfall only.
    MOYENNE if no item has shortfall > 0.
    """
    has_shortfall = False
    for item in shortage_items:
        s = item.get("shortfall", 0)
        if s > 0:
            has_shortfall = True
            if item.get("driver") == "condition":
                return "URGENTE"
    return "ÉLEVÉE" if has_shortfall else "MOYENNE"


def _build_wo_title(machine_id: int) -> str:
    return f"[P7] Parts preparation – Machine #{machine_id}"


def _build_wo_description(parts_demand: Dict[str, Any]) -> str:
    """Plain-language WO description with parts list. No ML jargon."""
    items = parts_demand.get("items", [])
    shortage = [i for i in items if i.get("shortfall", 0) > 0]
    horizon = parts_demand.get("horizon_days", 30)

    lines = [
        f"Predictive maintenance forecast — next {horizon} days.",
        f"Source: {parts_demand.get('source', 'forecast')}.",
        "",
        "Parts needed:",
    ]
    for item in items[:20]:
        name = item.get("name", f"Part {item.get('piece_id')}").title()
        expected = item.get("expected_qty", 0)
        on_hand = item.get("on_hand", 0)
        shortfall = item.get("shortfall", 0)
        driver = (
            "Condition-based" if item.get("driver") == "condition" else "Usage-based"
        )
        flag = f"  ← ORDER {int(shortfall + 0.999)}" if shortfall > 0 else ""
        lines.append(
            f"  • {name}: need {expected:.1f}, in stock {on_hand}{flag} ({driver})"
        )

    if len(items) > 20:
        lines.append(f"  … and {len(items) - 20} more parts.")

    lines += [
        "",
        f"ACTION: {len(shortage)} part(s) require procurement.",
        "This draft was generated automatically. Human approval required before any reservation.",
    ]
    return "\n".join(lines)


# ── Async DB operations ───────────────────────────────────────────────────


async def create_procurement_draft(
    machine_id: int,
    parts_demand: Dict[str, Any],
    created_by: Optional[int],
    db: AsyncSession,
) -> Optional[int]:
    """
    Create a DRAFT Ordres_travail from parts_demand shortfall data.

    Returns the new work order id, or None if:
    - parts_demand is None / has no items
    - an active PARTS_SHORTAGE alert for this machine already has a linked WO
      (dedup — one draft per machine at a time)

    The draft is NOT committed to DB here; caller commits.
    """
    from models.alertes import Alert, AlertType
    from models.ordres_travail import Ordres_travail, OrdreStatut

    if not parts_demand or not parts_demand.get("items"):
        return None

    items = parts_demand["items"]
    shortage = [i for i in items if i.get("shortfall", 0) > 0]

    # Dedup: check if active PARTS_SHORTAGE alert already has a WO linked
    existing_q = await db.execute(
        select(Alert).where(
            and_(
                Alert.machine_id == machine_id,
                Alert.alert_type == AlertType.PARTS_SHORTAGE,
                Alert.is_active,
                Alert.work_order_id.is_not(None),
            )
        )
    )
    if existing_q.scalar_one_or_none():
        logger.info(f"[P7] Draft WO already exists for machine {machine_id} — skipping")
        return None

    priority = _determine_priority(shortage)
    title = _build_wo_title(machine_id)
    description = _build_wo_description(parts_demand)
    due_date = datetime.now(timezone.utc) + timedelta(
        days=parts_demand.get("horizon_days", 30)
    )

    wo = Ordres_travail(
        titre=title,
        description=description,
        priorite=priority,
        machine_id=machine_id,
        statut=OrdreStatut.DRAFT,
        created_by=created_by,
        date_echeance=due_date,
    )
    db.add(wo)
    await db.flush()  # get wo.id without committing

    # Link WO to the active PARTS_SHORTAGE alert (dedup future calls)
    alert_q = await db.execute(
        select(Alert).where(
            and_(
                Alert.machine_id == machine_id,
                Alert.alert_type == AlertType.PARTS_SHORTAGE,
                Alert.is_active,
            )
        )
    )
    alert = alert_q.scalar_one_or_none()
    if alert:
        alert.work_order_id = wo.id
        alert.is_linked_to_wo = True

    logger.info(f"[P7] Draft WO #{wo.id} created for machine {machine_id} ({priority})")
    return wo.id


async def approve_procurement_draft(
    wo_id: int,
    approved_by: int,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Approve draft: DRAFT → SUBMITTED, enters normal CHEFTECH/ADMIN workflow.
    No inventory reservation here — happens when WO is validated downstream.
    """
    from models.ordres_travail import Ordres_travail, OrdreStatut

    result = await db.execute(select(Ordres_travail).where(Ordres_travail.id == wo_id))
    wo = result.scalar_one_or_none()
    if not wo:
        return {"success": False, "error": "Work order not found"}
    if wo.statut != OrdreStatut.DRAFT:
        return {
            "success": False,
            "error": f"WO is not a draft (status: {wo.statut.value})",
        }

    wo.statut = OrdreStatut.SUBMITTED
    wo.validated_by = approved_by
    await db.commit()
    await db.refresh(wo)
    logger.info(f"[P7] Draft WO #{wo_id} approved by user {approved_by} → SUBMITTED")
    return {"success": True, "wo_id": wo_id, "status": "SUBMITTED"}


async def reject_procurement_draft(
    wo_id: int,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Reject draft: DRAFT → ANNULÉ. Unlinks from PARTS_SHORTAGE alert.
    No reservation was ever made, so nothing to release.
    """
    from models.ordres_travail import Ordres_travail, OrdreStatut
    from models.alertes import Alert

    result = await db.execute(select(Ordres_travail).where(Ordres_travail.id == wo_id))
    wo = result.scalar_one_or_none()
    if not wo:
        return {"success": False, "error": "Work order not found"}
    if wo.statut != OrdreStatut.DRAFT:
        return {
            "success": False,
            "error": f"WO is not a draft (status: {wo.statut.value})",
        }

    wo.statut = OrdreStatut.ANNULÉ

    # Unlink from PARTS_SHORTAGE alert so future shortfalls can create a new draft
    alert_q = await db.execute(select(Alert).where(Alert.work_order_id == wo_id))
    alert = alert_q.scalar_one_or_none()
    if alert:
        alert.work_order_id = None
        alert.is_linked_to_wo = False

    await db.commit()
    logger.info(f"[P7] Draft WO #{wo_id} rejected → ANNULÉ")
    return {"success": True, "wo_id": wo_id, "status": "ANNULÉ"}
