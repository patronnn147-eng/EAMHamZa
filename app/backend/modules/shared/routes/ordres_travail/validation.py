import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.auth import require_role
from models.utilisateurs import Utilisateurs
from services.ordres_travail import Ordres_travailService
from ..ordres_travail.schemas import Ordres_travailValidationData, Ordres_travailResponse

router = APIRouter(prefix="/api/v1/entities/ordres_travail", tags=["ordres_travail"])
logger = logging.getLogger(__name__)


@router.post("/{id}/validate", response_model=Ordres_travailResponse)
async def validate_ordres_travail(
    id: int,
    data: Ordres_travailValidationData,
    db: AsyncSession = Depends(get_db),
    current_user: Utilisateurs = Depends(require_role(["CHEFTECH"]))
):
    """Validate or reject a Work Order (CHEFTECH only)"""
    logger.debug(f"Validating ordres_travail {id} with action: {data.action}")
    service = Ordres_travailService(db)
    
    order = await service.get_by_id(id)
    if not order:
        raise HTTPException(status_code=404, detail="Ordres_travail not found")
        
    update_dict = {}
    if data.action == "APPROVE":
        if not data.utilisateur_id:
            raise HTTPException(status_code=400, detail="utilisateur_id is required to approve & assign.")
        update_dict["statut"] = "VALIDE"
        update_dict["utilisateur_id"] = data.utilisateur_id
        update_dict["validated_by"] = current_user.id
        update_dict["date_validation"] = datetime.now()
    elif data.action == "REJECT":
        update_dict["statut"] = "REJETE"
        update_dict["validated_by"] = current_user.id
        update_dict["date_validation"] = datetime.now()
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
        
    result = await service.update(id, update_dict)
    return result
