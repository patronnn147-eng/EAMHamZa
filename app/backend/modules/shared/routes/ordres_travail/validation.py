import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.auth import require_role
from models.utilisateurs import Utilisateurs, UserRole
from models.ordres_travail import OrdreStatut
from services.ordres_travail import Ordres_travailService
from services.inventory import InventoryReservationService
from models.ordres_intervention import Ordres_intervention
from sqlalchemy import select
from ..ordres_travail.schemas import (
    Ordres_travailValidationData,
    Ordres_travailResponse,
)

router = APIRouter(prefix="/api/v1/entities/ordres_travail", tags=["ordres_travail"])
logger = logging.getLogger(__name__)


@router.post("/{id}/validate", response_model=Ordres_travailResponse)
async def validate_ordres_travail(
    id: int,
    data: Ordres_travailValidationData,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(require_role(["CHEFTECH"])),
):
    """Validate or reject a Work Order (CHEFTECH only)"""
    # Also allow TECHNICIEN to validate completed work
    if current_user.role not in [UserRole.CHEFTECH, UserRole.TECHNICIEN]:
        raise HTTPException(
            status_code=403, detail="Vous n'avez pas la permission pour cette action"
        )

    logger.debug(f"Validating ordres_travail {id} with action: {data.action}")
    service = Ordres_travailService(db)

    order = await service.get_by_id(id)
    if not order:
        raise HTTPException(status_code=404, detail="Ordres_travail not found")

    update_dict = {}
    if data.action == "APPROVE":
        if not data.utilisateur_id:
            raise HTTPException(
                status_code=400,
                detail="utilisateur_id is required to approve & assign.",
            )
        update_dict["statut"] = OrdreStatut.APPROVED
        update_dict["utilisateur_id"] = data.utilisateur_id
        update_dict["validated_by"] = current_user.id
        update_dict["date_validation"] = datetime.now()
    elif data.action == "REJECT":
        update_dict["statut"] = OrdreStatut.REJECTED
        update_dict["validated_by"] = current_user.id
        update_dict["date_validation"] = datetime.now()
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    result = await service.update(id, update_dict)

    # Release reservations for every linked intervention on REJECT
    if data.action == "REJECT":
        try:
            linked = (
                (
                    await db.execute(
                        select(Ordres_intervention.id).where(
                            Ordres_intervention.ordre_travail_id == id
                        )
                    )
                )
                .scalars()
                .all()
            )
            for itv_id in linked:
                try:
                    await InventoryReservationService(db).release_all(
                        intervention_id=itv_id, reason="wo-rejected", auto_commit=True
                    )
                except Exception as rls_exc:
                    logger.warning(
                        f"release_all on WO reject failed for itv {itv_id}: {rls_exc}"
                    )
        except Exception as scan_exc:
            logger.warning(
                f"Could not scan linked interventions for WO {id}: {scan_exc}"
            )

    return result


@router.post("/{id}/close", response_model=Ordres_travailResponse)
async def close_ordres_travail(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(require_role(["ADMIN"])),
):
    """Close a Work Order (ADMIN only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403, detail="Vous n'avez pas la permission pour cette action"
        )

    logger.debug(f"Closing ordres_travail {id}")
    service = Ordres_travailService(db)

    order = await service.get_by_id(id)
    if not order:
        raise HTTPException(status_code=404, detail="Ordres_travail not found")

    # Only allow closing VALIDATED orders
    if order.statut != OrdreStatut.VALIDATED:
        raise HTTPException(
            status_code=400, detail="Only validated work orders can be closed"
        )

    update_dict = {"statut": OrdreStatut.CLOSED}

    result = await service.update(id, update_dict)
    return result
