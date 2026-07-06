import logging
from datetime import datetime, timezone
from typing import List, Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs
from models.ordres_intervention import Ordres_intervention
from models.machines import Machines
from services.audit import AuditService, AuditEntityType
from ..schemas import InterventionRequestCreate, InterventionRequestResponse

router = APIRouter(prefix="/api/v1/chetop", tags=["chetop"])
logger = logging.getLogger(__name__)


@router.post(
    "/intervention-requests",
    response_model=InterventionRequestResponse,
    status_code=201,
)
async def create_intervention_request(
    data: InterventionRequestCreate,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """ChefOp requests an intervention (PDS)"""
    try:
        # Validate machine exists
        machine_result = await db.execute(
            select(Machines).where(Machines.id == data.machine_id)
        )
        machine = machine_result.scalar_one_or_none()
        if not machine:
            raise HTTPException(status_code=404, detail="Machine not found")

        new_request = Ordres_intervention(
            machine_id=data.machine_id,
            priority=data.priorite,
            problem_description=data.description,
            statut="PENDING_APPROVAL",
            date_intervention=datetime.now(timezone.utc),
            requested_at=datetime.now(timezone.utc),
            requested_by=current_user.id,
            ordre_travail_id=None,
            technicien_id=None,
            # New enhanced fields
            machine_category=data.machine_category,
            symptoms=data.symptoms,
            problem_start_time=data.problem_start_time,
            frequency=data.frequency,
            operating_state=data.operating_state,
            temperature=data.temperature,
            impact=data.impact,
            estimated_loss=data.estimated_loss,
            similar_issue_before=data.similar_issue_before,
            suggested_cause=data.suggested_cause,
            suggested_priority=data.suggested_priority,
            risk_score=data.risk_score,
        )

        db.add(new_request)
        await db.commit()
        await db.refresh(new_request)

        try:
            await AuditService(db).log_create(
                entity_type=AuditEntityType.INTERVENTION,
                entity_id=new_request.id,
                new_values={
                    "machine_id": data.machine_id,
                    "priority": data.priorite,
                    "description": data.description,
                    "statut": "PENDING_APPROVAL",
                },
                user_id=current_user.id,
                user_name=current_user.nom,
                entity_name=machine.nom,
            )
        except Exception:
            logger.warning(
                "Audit log failed for create intervention request %s", new_request.id
            )

        return InterventionRequestResponse(
            id=new_request.id,
            machine_id=new_request.machine_id,
            machine_nom=machine.nom,
            priorite=new_request.priority or "MOYENNE",
            description=new_request.problem_description or "",
            statut=new_request.statut,
            requested_at=new_request.requested_at,
        )
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error creating request: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/intervention-requests", response_model=List[InterventionRequestResponse])
async def get_my_intervention_requests(
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List ChefOp's own intervention requests"""
    try:
        query = (
            select(Ordres_intervention, Machines.nom.label("machine_nom"))
            .outerjoin(Machines, Ordres_intervention.machine_id == Machines.id)
            .where(Ordres_intervention.requested_by == current_user.id)
            .where(Ordres_intervention.archived_at.is_(None))
            .order_by(Ordres_intervention.requested_at.desc())
        )

        result = await db.execute(query)
        rows = result.all()

        return [
            InterventionRequestResponse(
                id=itv.id,
                machine_id=itv.machine_id,
                machine_nom=machine_nom,
                priorite=itv.priority or "MOYENNE",
                description=itv.problem_description or "",
                statut=itv.statut,
                requested_at=itv.requested_at,
                rejection_reason=itv.rejection_reason,
            )
            for itv, machine_nom in rows
        ]
    except Exception as e:
        logger.exception(f"Error listing requests: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
