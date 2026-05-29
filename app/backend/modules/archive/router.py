"""Archive API — per-module listing + admin reactivate + manual sweep.

Routes:
  GET  /api/v1/archive/{module}        — paginated archived items (role-scoped)
  POST /api/v1/archive/{module}/{id}/reactivate  — admin/cheftech only
  POST /api/v1/archive/sweep           — manual sweep trigger (admin only)
  POST /api/v1/archive/purge           — manual purge trigger (admin only)
  GET  /api/v1/archive/counts          — per-module archived totals (for sidebar badge)

`module` ∈ {planning_taches, ordres_travail, ordres_intervention, plannings}.

Role scoping:
- TECHNICIEN sees only items where they're the assigned technician
- CHEFTECH/CHETOP see all items in their scope
- ADMIN sees everything
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_db
from dependencies.auth import require_role
from models.utilisateurs import Utilisateurs
from services.archive import ARCHIVE_RULES, ArchiveService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/archive", tags=["archive"])

VALID_MODULES = {r.module for r in ARCHIVE_RULES}

# Role → which column gates user-visibility for archived items
SCOPE_COLUMN_BY_MODULE_ROLE = {
    ("planning_taches", "TECHNICIEN"):    "technicien_id",
    ("ordres_travail", "TECHNICIEN"):     "utilisateur_id",
    ("ordres_intervention", "TECHNICIEN"): "technician_id",
    # CHEFTECH/CHETOP/ADMIN see all by default
}


@router.get("/counts")
async def get_archive_counts(
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return {module: count} of archived items visible to the caller."""
    counts: Dict[str, int] = {}
    role = (current_user.role or "").upper()

    svc = ArchiveService(db)
    for rule in ARCHIVE_RULES:
        scope_col = SCOPE_COLUMN_BY_MODULE_ROLE.get((rule.module, role))
        archived_col = getattr(rule.model, "archived_at")
        conditions = [archived_col.is_not(None)]
        if scope_col and hasattr(rule.model, scope_col):
            conditions.append(getattr(rule.model, scope_col) == current_user.id)
        stmt = select(func.count()).select_from(rule.model).where(and_(*conditions))
        counts[rule.module] = (await db.execute(stmt)).scalar() or 0

    return {"counts": counts, "total": sum(counts.values())}


@router.get("/{module}")
async def list_archived(
    module: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    search: Optional[str] = Query(None, max_length=200),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List archived items for a module, role-scoped + paginated."""
    if module not in VALID_MODULES:
        raise HTTPException(status_code=404, detail=f"Module inconnu: {module}")

    role = (current_user.role or "").upper()
    scope_col = SCOPE_COLUMN_BY_MODULE_ROLE.get((module, role))

    skip = (page - 1) * size
    svc = ArchiveService(db)
    try:
        result = await svc.list_archived(
            module=module,
            skip=skip,
            limit=size,
            search=search,
            date_from=date_from,
            date_to=date_to,
            user_filter_column=scope_col,
            user_id_filter=current_user.id if scope_col else None,
        )

        items = result["items"]  # list of model instances
        # Serialize each model — extract common fields only
        out = []
        for it in items:
            row: Dict[str, Any] = {
                "id": it.id,
                "archived_at": it.archived_at.isoformat() if getattr(it, "archived_at", None) else None,
                "archive_reason": getattr(it, "archive_reason", None),
            }
            # Common identity fields
            for attr in ("titre", "identifiant_planning", "rapport", "description",
                         "problem_description", "priorite", "priority", "statut",
                         "planning_statut", "date_echeance", "date_fin",
                         "date_debut", "date_intervention", "machine_id",
                         "technicien_id", "technician_id", "utilisateur_id"):
                if hasattr(it, attr):
                    v = getattr(it, attr)
                    if isinstance(v, datetime):
                        row[attr] = v.isoformat()
                    else:
                        # Skip non-serializable enum-like objects gracefully
                        try:
                            row[attr] = v.value if hasattr(v, "value") and not isinstance(v, (int, str, float)) else v
                        except Exception:
                            row[attr] = str(v) if v is not None else None
            out.append(row)

        return {
            "module": module,
            "items": out,
            "total": result["total"],
            "page": page,
            "size": size,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"list_archived {module} failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{module}/{item_id}/reactivate")
async def reactivate_archived(
    module: str,
    item_id: int,
    current_user: Utilisateurs = Depends(require_role(["ADMIN", "CHEFTECH"])),
    db: AsyncSession = Depends(get_db),
):
    """Reactivate an archived item — sets archived_at=NULL.
    Admin + CHEFTECH only.
    """
    if module not in VALID_MODULES:
        raise HTTPException(status_code=404, detail=f"Module inconnu: {module}")

    try:
        ok = await ArchiveService(db).reactivate(module=module, item_id=item_id, auto_commit=True)
        if not ok:
            raise HTTPException(status_code=404, detail="Item non archivé ou introuvable")
        return {"module": module, "item_id": item_id, "status": "reactivated"}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"reactivate {module}/{item_id} failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sweep")
async def trigger_sweep_now(
    _current_user: Utilisateurs = Depends(require_role(["ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """Run the archive sweep immediately (admin button — bypasses Celery beat)."""
    try:
        results = await ArchiveService(db).archive_past_due(auto_commit=True)
        return {"status": "ok", "archived": results, "total": sum(results.values())}
    except Exception as e:
        logger.error(f"manual archive sweep failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/purge")
async def trigger_purge_now(
    retention_days: int = Query(30, ge=1, le=3650),
    _current_user: Utilisateurs = Depends(require_role(["ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """Run the purge sweep immediately (admin button — bypasses Celery beat).
    DANGEROUS: hard-deletes archived rows older than retention_days.
    """
    try:
        results = await ArchiveService(db).purge_old(retention_days=retention_days, auto_commit=True)
        return {"status": "ok", "purged": results, "total": sum(results.values()), "retention_days": retention_days}
    except Exception as e:
        logger.error(f"manual archive purge failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
