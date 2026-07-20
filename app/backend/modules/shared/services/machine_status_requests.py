"""
Gated approval for technician-proposed machine status changes.

Mirrors modules/ml/services/parts_drafts.py's guarded-draft pattern: a
technician's WO-completion input becomes a PENDING request; only a CHEFTECH
approval writes it to Machines.statut. ADMIN never acts here — approve/reject
write an AuditLog row, surfaced by the existing AuditLogViewer.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def create_status_change_request(
    machine_id: int,
    to_status: str,
    requested_by: Optional[int],
    source_intervention_id: Optional[int],
    db: AsyncSession,
) -> Optional[int]:
    """
    Create a PENDING machine status change request.

    Returns None (no-op) if:
    - the machine doesn't exist
    - to_status already equals the machine's current statut (nothing to propose)

    Supersedes (-> REJECTED, with a note) any existing PENDING request for
    this machine before creating the new one — "last technician's call" per
    request, but nothing is deleted. The new row is flushed (not committed);
    caller commits as part of its own transaction (WO completion).
    """
    from models.machines import Machines
    from models.machine_status_change_request import (
        MachineStatusChangeRequest,
        RequestStatus,
    )

    machine = await db.scalar(select(Machines).where(Machines.id == machine_id))
    if not machine:
        return None

    from_status = machine.statut
    if from_status == to_status:
        return None

    existing_q = await db.execute(
        select(MachineStatusChangeRequest).where(
            MachineStatusChangeRequest.machine_id == machine_id,
            MachineStatusChangeRequest.status == RequestStatus.PENDING,
        )
    )
    for existing in existing_q.scalars().all():
        existing.status = RequestStatus.REJECTED
        existing.reviewed_at = datetime.now(timezone.utc)
        existing.review_note = "Superseded by newer request"

    request = MachineStatusChangeRequest(
        machine_id=machine_id,
        from_status=from_status,
        to_status=to_status,
        status=RequestStatus.PENDING,
        source_intervention_id=source_intervention_id,
        requested_by=requested_by,
    )
    db.add(request)
    await db.flush()  # get request.id without committing
    logger.info(
        f"Machine status change request #{request.id} created for machine "
        f"{machine_id}: {from_status} -> {to_status}"
    )
    return request.id


async def approve_status_change_request(
    request_id: int,
    approved_by: int,
    db: AsyncSession,
    approved_by_name: Optional[str] = None,
) -> Dict[str, Any]:
    """PENDING -> APPROVED. Sets Machines.statut = to_status, writes AuditLog."""
    from models.machines import Machines
    from models.machine_status_change_request import (
        MachineStatusChangeRequest,
        RequestStatus,
    )
    from services.audit import AuditService, AuditEntityType

    request = await db.scalar(
        select(MachineStatusChangeRequest).where(
            MachineStatusChangeRequest.id == request_id
        )
    )
    if not request:
        return {"success": False, "error": "Request not found"}
    if request.status != RequestStatus.PENDING:
        return {
            "success": False,
            "error": f"Request is not pending (status: {request.status.value})",
        }

    machine = await db.scalar(select(Machines).where(Machines.id == request.machine_id))
    if not machine:
        return {"success": False, "error": "Machine not found"}

    machine.statut = request.to_status
    request.status = RequestStatus.APPROVED
    request.reviewed_by = approved_by
    request.reviewed_at = datetime.now(timezone.utc)

    try:
        await AuditService(db).log_update(
            entity_type=AuditEntityType.MACHINE,
            entity_id=request.machine_id,
            old_values={"statut": request.from_status},
            new_values={"statut": request.to_status},
            user_id=approved_by,
            user_name=approved_by_name,
            entity_name=machine.nom,
        )
    except Exception:
        logger.warning(f"Audit log failed for status request #{request_id} approval")

    await db.commit()
    logger.info(
        f"Machine status change request #{request_id} approved by user {approved_by}"
    )
    return {
        "success": True,
        "request_id": request_id,
        "status": "APPROVED",
        "statut": machine.statut,
    }


async def reject_status_change_request(
    request_id: int,
    rejected_by: int,
    note: Optional[str],
    db: AsyncSession,
    rejected_by_name: Optional[str] = None,
) -> Dict[str, Any]:
    """PENDING -> REJECTED. Machines.statut untouched, writes AuditLog.

    `statut` is deliberately NOT in the audit old/new values here — it
    doesn't change on reject, and AuditService.log_update() only records a
    diff for keys whose value differs between old_values/new_values;
    identical values on both sides would produce an empty, useless entry.
    """
    from models.machines import Machines
    from models.machine_status_change_request import (
        MachineStatusChangeRequest,
        RequestStatus,
    )
    from services.audit import AuditService, AuditEntityType

    request = await db.scalar(
        select(MachineStatusChangeRequest).where(
            MachineStatusChangeRequest.id == request_id
        )
    )
    if not request:
        return {"success": False, "error": "Request not found"}
    if request.status != RequestStatus.PENDING:
        return {
            "success": False,
            "error": f"Request is not pending (status: {request.status.value})",
        }

    machine = await db.scalar(select(Machines).where(Machines.id == request.machine_id))

    request.status = RequestStatus.REJECTED
    request.reviewed_by = rejected_by
    request.reviewed_at = datetime.now(timezone.utc)
    request.review_note = note

    try:
        await AuditService(db).log_update(
            entity_type=AuditEntityType.MACHINE,
            entity_id=request.machine_id,
            old_values={
                "request_status": "PENDING",
                "proposed_statut": request.to_status,
            },
            new_values={
                "request_status": "REJECTED",
                "proposed_statut": request.to_status,
                "review_note": note or "",
            },
            user_id=rejected_by,
            user_name=rejected_by_name,
            entity_name=machine.nom if machine else None,
        )
    except Exception:
        logger.warning(f"Audit log failed for status request #{request_id} rejection")

    await db.commit()
    logger.info(
        f"Machine status change request #{request_id} rejected by user {rejected_by}"
    )
    return {"success": True, "request_id": request_id, "status": "REJECTED"}


async def list_pending_requests(db: AsyncSession) -> List[Dict[str, Any]]:
    """Joined view for the CHEFTECH queue page, oldest-first."""
    from models.machines import Machines
    from models.machine_status_change_request import (
        MachineStatusChangeRequest,
        RequestStatus,
    )
    from models.utilisateurs import Utilisateurs

    result = await db.execute(
        select(MachineStatusChangeRequest, Machines, Utilisateurs)
        .join(Machines, MachineStatusChangeRequest.machine_id == Machines.id)
        .outerjoin(
            Utilisateurs, MachineStatusChangeRequest.requested_by == Utilisateurs.id
        )
        .where(MachineStatusChangeRequest.status == RequestStatus.PENDING)
        .order_by(MachineStatusChangeRequest.requested_at.asc())
    )
    rows = result.all()
    return [
        {
            "id": req.id,
            "machine_id": req.machine_id,
            "machine_name": machine.nom,
            "from_status": req.from_status,
            "to_status": req.to_status,
            "requested_by": req.requested_by,
            "requested_by_name": user.nom if user else None,
            "requested_at": req.requested_at.isoformat() if req.requested_at else None,
            "source_intervention_id": req.source_intervention_id,
        }
        for req, machine, user in rows
    ]
