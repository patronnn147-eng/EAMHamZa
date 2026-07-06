"""Pending pieces router — submission + admin review queue."""

import logging
from typing import Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.auth import require_role
from models.utilisateurs import Utilisateurs
from schemas.pagination import PaginatedResponse
from schemas.piece import PieceCreate
from schemas.stock import (
    PendingPieceItem,
    PendingPieceMatchRequest,
    PendingPieceRejectRequest,
    PendingPieceResponse,
)
from services.audit import AuditEntityType, AuditService
from services.inventory import PendingPieceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/inventory/pending", tags=["inventory-pending"])


# Roles allowed to *submit* a pending piece (anybody who can complete an
# intervention: TECHNICIEN + management roles).
ROLES_SUBMIT = ["TECHNICIEN", "CHEFTECH", "CHETOP", "ADMIN"]
# Roles allowed to *review* (admin queue): catalog curators / warehouse mgmt.
ROLES_REVIEW = ["ADMIN", "CHEFTECH"]


@router.post("", response_model=PendingPieceResponse, status_code=201, responses={400: {"description": "Bad Request"}, 500: {"description": "Internal server error"}})
async def submit_pending_piece(
    *, data: PendingPieceItem,
    intervention_id: Annotated[Optional[int], Query(description="Link to intervention")] = None,
    current_user: Annotated[Utilisateurs, Depends(require_role(ROLES_SUBMIT))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Submit an uncatalogued piece during an intervention.

    Creates the pending row AND its placeholder mouvement_stock row in one
    atomic transaction. The placeholder preserves the actual submission
    timestamp regardless of how long admin review takes.
    """
    try:
        svc = PendingPieceService(db)
        pp = await svc.create_with_placeholder(
            name=data.name,
            quantity=data.quantity,
            unit=data.unit,
            category=data.category,
            photo_object_key=data.photo_object_key,
            notes=data.notes,
            intervention_id=intervention_id,
            submitted_by=current_user.id,
        )

        try:
            await AuditService(db).log_create(
                entity_type=AuditEntityType.INVENTORY,
                entity_id=pp.id,
                new_values={
                    "name": pp.name,
                    "quantity": float(pp.quantity),
                    "intervention_id": intervention_id,
                },
                user_id=current_user.id,
                user_name=current_user.nom,
                entity_name=pp.name,
            )
        except Exception:
            logger.warning("Audit log failed for pending piece submit")

        return PendingPieceResponse.model_validate(
            {
                "id": pp.id,
                "intervention_id": pp.intervention_id,
                "submitted_by": pp.submitted_by,
                "submitted_by_name": current_user.nom,
                "name": pp.name,
                "category": pp.category,
                "quantity": pp.quantity,
                "unit": pp.unit,
                "photo_object_key": pp.photo_object_key,
                "notes": pp.notes,
                "status": pp.status,
                "matched_piece_id": pp.matched_piece_id,
                "matched_piece_name": None,
                "reviewed_by": pp.reviewed_by,
                "reviewed_at": pp.reviewed_at,
                "rejection_reason": pp.rejection_reason,
                "created_at": pp.created_at,
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"submit_pending_piece failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=PaginatedResponse[PendingPieceResponse], responses={500: {"description": "Internal server error"}})
async def list_pending(
    *, status: Annotated[Optional[str], Query(
        description="Filter by status (or 'ALL')"
    )] = "PENDING_REVIEW",
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=200)] = 50,
    _current_user: Annotated[Utilisateurs, Depends(require_role(ROLES_REVIEW))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Admin queue. Default shows only PENDING_REVIEW; pass status=ALL for full history."""
    try:
        svc = PendingPieceService(db)
        skip = (page - 1) * size
        filter_status: Optional[str] = status if status and status != "ALL" else None
        result = await svc.list_pending(status=filter_status, skip=skip, limit=size)
        items = [PendingPieceResponse.model_validate(r) for r in result["items"]]
        return PaginatedResponse.create(
            items=items, total=result["total"], page=page, size=size
        )
    except Exception as e:
        logger.exception(f"list_pending failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/{pending_id}/match", response_model=PendingPieceResponse, responses={400: {"description": "Bad Request"}, 500: {"description": "Internal server error"}})
async def match_pending(
    pending_id: int,
    data: PendingPieceMatchRequest,
    current_user: Annotated[Utilisateurs, Depends(require_role(ROLES_REVIEW))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Match an existing catalog piece — in-place mvt conversion preserves chronology."""
    try:
        svc = PendingPieceService(db)
        pp = await svc.match_to_existing(
            pending_id=pending_id,
            matched_piece_id=data.matched_piece_id,
            reviewed_by=current_user.id,
        )

        try:
            await AuditService(db).log_update(
                entity_type=AuditEntityType.INVENTORY,
                entity_id=pp.id,
                old_values={"status": "PENDING_REVIEW"},
                new_values={
                    "status": "MATCHED",
                    "matched_piece_id": pp.matched_piece_id,
                },
                user_id=current_user.id,
                user_name=current_user.nom,
                entity_name=pp.name,
            )
        except Exception:
            logger.warning("Audit log failed for pending piece match")

        return PendingPieceResponse.model_validate(
            {
                "id": pp.id,
                "intervention_id": pp.intervention_id,
                "submitted_by": pp.submitted_by,
                "submitted_by_name": None,
                "name": pp.name,
                "category": pp.category,
                "quantity": pp.quantity,
                "unit": pp.unit,
                "photo_object_key": pp.photo_object_key,
                "notes": pp.notes,
                "status": pp.status,
                "matched_piece_id": pp.matched_piece_id,
                "matched_piece_name": None,
                "reviewed_by": pp.reviewed_by,
                "reviewed_at": pp.reviewed_at,
                "rejection_reason": pp.rejection_reason,
                "created_at": pp.created_at,
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"match_pending failed for {pending_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{pending_id}/create-piece", response_model=PendingPieceResponse, responses={400: {"description": "Bad Request"}, 500: {"description": "Internal server error"}})
async def create_from_pending(
    pending_id: int,
    data: PieceCreate,
    current_user: Annotated[Utilisateurs, Depends(require_role(ROLES_REVIEW))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a brand-new catalog piece from a pending submission."""
    try:
        svc = PendingPieceService(db)
        pp = await svc.create_new_piece(
            pending_id=pending_id,
            new_piece_data=data.model_dump(),
            reviewed_by=current_user.id,
        )

        try:
            await AuditService(db).log_update(
                entity_type=AuditEntityType.INVENTORY,
                entity_id=pp.id,
                old_values={"status": "PENDING_REVIEW"},
                new_values={
                    "status": "CREATED",
                    "matched_piece_id": pp.matched_piece_id,
                },
                user_id=current_user.id,
                user_name=current_user.nom,
                entity_name=pp.name,
            )
        except Exception:
            logger.warning("Audit log failed for create_from_pending")

        return PendingPieceResponse.model_validate(
            {
                "id": pp.id,
                "intervention_id": pp.intervention_id,
                "submitted_by": pp.submitted_by,
                "submitted_by_name": None,
                "name": pp.name,
                "category": pp.category,
                "quantity": pp.quantity,
                "unit": pp.unit,
                "photo_object_key": pp.photo_object_key,
                "notes": pp.notes,
                "status": pp.status,
                "matched_piece_id": pp.matched_piece_id,
                "matched_piece_name": None,
                "reviewed_by": pp.reviewed_by,
                "reviewed_at": pp.reviewed_at,
                "rejection_reason": pp.rejection_reason,
                "created_at": pp.created_at,
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(
            f"create_from_pending failed for {pending_id}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/{pending_id}/reject", response_model=PendingPieceResponse, responses={400: {"description": "Bad Request"}, 500: {"description": "Internal server error"}})
async def reject_pending(
    pending_id: int,
    data: PendingPieceRejectRequest,
    current_user: Annotated[Utilisateurs, Depends(require_role(ROLES_REVIEW))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Reject a pending submission. Placeholder mvt marked REJECTED, no stock change."""
    try:
        svc = PendingPieceService(db)
        pp = await svc.reject(
            pending_id=pending_id,
            rejection_reason=data.rejection_reason,
            reviewed_by=current_user.id,
        )

        try:
            await AuditService(db).log_update(
                entity_type=AuditEntityType.INVENTORY,
                entity_id=pp.id,
                old_values={"status": "PENDING_REVIEW"},
                new_values={
                    "status": "REJECTED",
                    "rejection_reason": pp.rejection_reason,
                },
                user_id=current_user.id,
                user_name=current_user.nom,
                entity_name=pp.name,
            )
        except Exception:
            logger.warning("Audit log failed for reject_pending")

        return PendingPieceResponse.model_validate(
            {
                "id": pp.id,
                "intervention_id": pp.intervention_id,
                "submitted_by": pp.submitted_by,
                "submitted_by_name": None,
                "name": pp.name,
                "category": pp.category,
                "quantity": pp.quantity,
                "unit": pp.unit,
                "photo_object_key": pp.photo_object_key,
                "notes": pp.notes,
                "status": pp.status,
                "matched_piece_id": pp.matched_piece_id,
                "matched_piece_name": None,
                "reviewed_by": pp.reviewed_by,
                "reviewed_at": pp.reviewed_at,
                "rejection_reason": pp.rejection_reason,
                "created_at": pp.created_at,
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"reject_pending failed for {pending_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
