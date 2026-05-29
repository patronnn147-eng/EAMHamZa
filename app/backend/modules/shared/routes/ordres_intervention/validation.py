import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.auth import require_role
from models.utilisateurs import Utilisateurs, UserRole
from models.ordres_travail import OrdreStatut
from services.audit import AuditService, AuditEntityType
from services.ordres_intervention import Ordres_interventionService
from services.inventory import InventoryReservationService
from ..ordres_intervention.schemas import Ordres_interventionValidationData, Ordres_interventionResponse

router = APIRouter(prefix="/api/v1/entities/ordres_intervention", tags=["ordres_intervention"])
logger = logging.getLogger(__name__)


@router.post("/{id}/validate", response_model=Ordres_interventionResponse)
async def validate_ordres_intervention(
    id: int,
    data: Ordres_interventionValidationData,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(require_role(["CHEFTECH"]))
):
    """Validate or reject an Intervention (CHEFTECH only)"""
    logger.debug(f"Validating ordres_intervention {id} with action: {data.action}")
    service = Ordres_interventionService(db)
    
    intervention = await service.get_by_id(id)
    if not intervention:
        raise HTTPException(status_code=404, detail="Ordres_intervention not found")
        
    update_dict = {}
    if data.action == "APPROVE":
        update_dict["statut"] = "APPROVED"
        update_dict["approved_by"] = current_user.id
        update_dict["approved_at"] = datetime.now()

        try:
            from services.ordres_travail import Ordres_travailService

            wo_service = Ordres_travailService(db)

            if not intervention.machine_id:
                raise HTTPException(status_code=400, detail="Cannot create Work Order: Intervention must be associated with a machine.")

            new_wo = await wo_service.create({
                "titre": f"[Intervention Acceptée] Demande #{id}",
                "description": intervention.problem_description or "Demande d'intervention validée par le ChefTech",
                "priorite": intervention.priority or "MOYENNE",
                "statut": OrdreStatut.ASSIGNED,  # Use new enum
                "machine_id": intervention.machine_id,
                "utilisateur_id": intervention.technician_id,
                "created_by": intervention.technician_id,
                "validated_by": current_user.id,
                "date_validation": datetime.now(),
            })
            
            update_dict["ordre_travail_id"] = new_wo.id
            logger.info(f"Created linked Work Order #{new_wo.id} for Intervention #{id}")
        except Exception as e:
            logger.error(f"Failed to create linked Work Order for accepted intervention #{id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to create linked Work Order.")

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
