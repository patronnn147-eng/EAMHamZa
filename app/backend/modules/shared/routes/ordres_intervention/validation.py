import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.auth import require_role
from models.utilisateurs import Utilisateurs
from models.ordres_travail import OrdreStatut
from services.audit import AuditService, AuditEntityType
from services.ordres_intervention import OrdresInterventionService
from services.inventory import InventoryReservationService
from .schemas import (
    OrdresInterventionValidationData,
    OrdresInterventionResponse,
)
from typing import Annotated

router = APIRouter(
    prefix="/api/v1/entities/ordres_intervention", tags=["OrdresIntervention"]
)
logger = logging.getLogger(__name__)


@router.post("/{id}/validate", response_model=OrdresInterventionResponse, responses={400: {"description": "Cannot create Work Order: Intervention must be associated with a machine.; Invalid action"}, 404: {"description": "OrdresIntervention not found"}, 500: {"description": "Failed to create linked Work Order."}})
async def validate_OrdresIntervention(
    id: int,
    data: OrdresInterventionValidationData,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(require_role(["CHEFTECH"]))],
):
    """Validate or reject an Intervention (CHEFTECH only)"""
    logger.debug(f"Validating OrdresIntervention {id} with action: {data.action}")
    service = OrdresInterventionService(db)

    intervention = await service.get_by_id(id)
    if not intervention:
        raise HTTPException(status_code=404, detail="OrdresIntervention not found")

    update_dict = {}
    if data.action == "APPROVE":
        update_dict["statut"] = "APPROVED"
        update_dict["approved_by"] = current_user.id
        update_dict["approved_at"] = datetime.now()

        try:
            from services.ordres_travail import OrdresTravailService

            wo_service = OrdresTravailService(db)

            if not intervention.machine_id:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot create Work Order: Intervention must be associated with a machine.",
                )

            new_wo = await wo_service.create(
                {
                    "titre": f"[Intervention Acceptée] Demande #{id}",
                    "description": intervention.problem_description
                    or "Demande d'intervention validée par le ChefTech",
                    "priorite": intervention.priority or "MOYENNE",
                    "statut": OrdreStatut.ASSIGNED,  # Use new enum
                    "machine_id": intervention.machine_id,
                    "utilisateur_id": intervention.technician_id,
                    "created_by": intervention.technician_id,
                    "validated_by": current_user.id,
                    "date_validation": datetime.now(),
                }
            )

            update_dict["ordre_travail_id"] = new_wo.id
            safe_wo_id = str(new_wo.id).replace("\r", "").replace("\n", "")
            logger.info(
                f"Created linked Work Order #{safe_wo_id} for Intervention #{id}"
            )
        except Exception as e:
            safe_exc = str(e).replace("\r", "").replace("\n", "")
            logger.error(
                f"Failed to create linked Work Order for accepted intervention #{id}: {safe_exc}"
            )
            raise HTTPException(
                status_code=500, detail="Failed to create linked Work Order."
            )

    elif data.action == "REJECT":
        update_dict["statut"] = "DECLINED"
        update_dict["approved_by"] = current_user.id
        update_dict["approved_at"] = datetime.now()
        update_dict["rejection_reason"] = data.rejection_reason
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    old_statut = intervention.statut
    result = await service.update(id, update_dict)

    # Release reservations if intervention rejected (defensive — usually no rows match)
    if data.action == "REJECT":
        try:
            await InventoryReservationService(db).release_all(
                intervention_id=id, reason="rejected", auto_commit=True
            )
        except Exception as rls_exc:
            logger.warning(f"release_all on intervention reject failed: {rls_exc}")

    try:
        await AuditService(db).log_update(
            entity_type=AuditEntityType.INTERVENTION,
            entity_id=id,
            old_values={"statut": old_statut},
            new_values={"statut": update_dict.get("statut"), "action": data.action},
            user_id=current_user.id,
            user_name=current_user.nom,
        )
    except Exception:
        logger.warning("Audit log failed for validate intervention %s", id)

    return result


@router.post(
    "/{id}/complete-validation",
    response_model=OrdresInterventionResponse,
    responses={
        400: {"description": "Intervention must be completed with a root-cause diagnosis before validation"},
        404: {"description": "OrdresIntervention not found"},
    },
)
async def complete_validation_ordres_intervention(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Utilisateurs, Depends(require_role(["CHEFTECH"]))],
):
    """Mark a completed, diagnosed intervention as VALIDATED (PDCA CHECK -> ACT).

    Distinct from POST /{id}/validate, which approves a technician's *request*
    for a new intervention and creates a linked Work Order — that endpoint is
    for the pre-work approval workflow, not for closing out finished work.
    """
    service = OrdresInterventionService(db)

    intervention = await service.get_by_id(id)
    if not intervention:
        raise HTTPException(status_code=404, detail="OrdresIntervention not found")

    if intervention.statut != "TERMINÉ" or not intervention.actual_failure_type:
        raise HTTPException(
            status_code=400,
            detail="Intervention must be completed with a root-cause diagnosis before validation",
        )

    old_statut = intervention.statut
    result = await service.update(
        id,
        {
            "statut": "VALIDATED",
            "approved_by": current_user.id,
            "approved_at": datetime.now(),
        },
    )

    try:
        await AuditService(db).log_update(
            entity_type=AuditEntityType.INTERVENTION,
            entity_id=id,
            old_values={"statut": old_statut},
            new_values={"statut": "VALIDATED"},
            user_id=current_user.id,
            user_name=current_user.nom,
        )
    except Exception:
        logger.warning("Audit log failed for complete-validation intervention %s", id)

    return result
