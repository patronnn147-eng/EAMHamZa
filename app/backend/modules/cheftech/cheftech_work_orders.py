from datetime import datetime, timezone
import io
import logging

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.pagination import PaginatedResponse

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs, UserRole
from models.ordres_travail import OrdresTravail
from models.machines import Machines
from models.ordres_intervention import OrdresIntervention
from typing import Annotated

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/cheftech/work-orders-table", tags=["cheftech-work-orders"]
)


def _require_cheftech(current_user: Utilisateurs):
    if current_user.role not in [UserRole.CHEFTECH, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Forbidden: ChefTech only")


def _itv_attr(itv, attr, default=None):
    """Return attribute from intervention ORM object, or default if itv is None."""
    return getattr(itv, attr, default) if itv else default


def _calc_duration(wo, now: datetime):
    """Return (duration_min, live_seconds) based on WO dates."""
    if wo.date_fin and wo.date_debut:
        return int((wo.date_fin - wo.date_debut).total_seconds() / 60), None
    if wo.date_debut:
        return None, int((now - wo.date_debut.replace(tzinfo=None)).total_seconds())
    return None, None


def _build_wo_row(wo, m_nom, u_nom, u_email, itv, now: datetime) -> dict:
    """Build the output dict for one work-order row in the list response."""
    duration_min, live_seconds = _calc_duration(wo, now)
    return {
        "id": wo.id,
        "titre": wo.titre,
        "machine_nom": m_nom or "N/A",
        "technicien_id": _itv_attr(itv, "technician_id"),
        "technicien_nom": u_nom or "N/A",
        "technicien_email": u_email or "N/A",
        "intervention_id": _itv_attr(itv, "id"),
        "statut": wo.statut,
        "priorite": wo.priorite,
        "created_at": wo.created_at.isoformat() if wo.created_at else None,
        "date_debut": wo.date_debut.isoformat() if wo.date_debut else None,
        "date_fin": wo.date_fin.isoformat() if wo.date_fin else None,
        "duration_min": duration_min,
        "live_seconds": live_seconds,
        "rapport": wo.rapport,
        "intervention_type": _itv_attr(itv, "intervention_type"),
        "machine_status_after": _itv_attr(itv, "machine_status_after"),
        "plan_hypothesis": _itv_attr(itv, "plan_hypothesis"),
        "root_cause_category": _itv_attr(itv, "root_cause_category"),
        "root_cause_description": _itv_attr(itv, "root_cause_description"),
        "actions_performed": _itv_attr(itv, "actions_performed"),
        "parts_replaced": _itv_attr(itv, "legacy_parts_text"),
        "tools_used": _itv_attr(itv, "tools_used"),
        "check_resolved": _itv_attr(itv, "check_resolved"),
        "check_verification_method": _itv_attr(itv, "check_verification_method"),
        "act_preventive_actions": _itv_attr(itv, "act_preventive_actions"),
        "act_recommendations": _itv_attr(itv, "act_recommendations"),
    }


async def _fetch_consumed_summary(db: AsyncSession, itv) -> str | None:
    """Query the intervention_consumption_summary VIEW; returns formatted string or None."""
    if itv is None:
        return None
    try:
        _row = (await db.execute(
            text("SELECT parts_replaced_json FROM intervention_consumption_summary WHERE intervention_id = :iid"),
            {"iid": itv.id},
        )).first()
        if not _row or not _row[0]:
            return None
        import json as _json
        data = _row[0] if isinstance(_row[0], list) else _json.loads(_row[0])
        parts = []
        for x in data:
            part = f"{x.get('piece_name', '?')} ({x.get('used', '0')}{x.get('unit', '')}"
            if float(x.get("returned", 0) or 0):
                part += f", retour={x.get('returned', '0')}"
            if float(x.get("wasted", 0) or 0):
                part += f", rebut={x.get('wasted', '0')}"
            parts.append(part + ")")
        return ", ".join(parts)
    except Exception:
        return None


def _itv_str(itv, attr, default="N/A"):
    """Return attribute from intervention ORM, or default for falsy/absent values."""
    return (getattr(itv, attr, None) or default) if itv else default


def _autofit_columns(worksheet) -> None:
    """Set each Excel column width to fit its longest value (max 60 chars)."""
    for col_cells in worksheet.columns:
        max_length = max(
            (len(str(cell.value)) for cell in col_cells if cell.value),
            default=0,
        )
        worksheet.column_dimensions[col_cells[0].column_letter].width = min(max_length + 4, 60)


def _build_export_flat_row(wo, m_nom, u_nom, u_email, itv, consumed_summary, duration_min) -> dict:
    """Build the flat dict used as a single Excel row for a work-order export."""
    _fmt = lambda d: d.strftime("%Y-%m-%d %H:%M") if d else "N/A"  # noqa: E731
    return {
        "ID OT": wo.id,
        "Titre": wo.titre or "N/A",
        "Machine": m_nom or "N/A",
        "Technicien": u_nom or "N/A",
        "Email Technicien": u_email or "N/A",
        "Date Création": _fmt(wo.created_at),
        "Date Début": _fmt(wo.date_debut),
        "Date Fin": _fmt(wo.date_fin),
        "Durée (min)": duration_min,
        "Statut OT": wo.statut,
        "Priorité": wo.priorite,
        "Rapport Brut": wo.rapport or "N/A",
        "ID Intervention": itv.id if itv else "N/A",
        "Priorité Intervention": _itv_str(itv, "priority"),
        "Symptômes": _itv_str(itv, "symptoms"),
        "Impact": _itv_str(itv, "impact"),
        "Fréquence": _itv_str(itv, "frequency"),
        "Score de Risque": _itv_str(itv, "risk_score"),
        "Type d'intervention": _itv_str(itv, "intervention_type"),
        "État Machine Après": _itv_str(itv, "machine_status_after"),
        "PLAN - Hypothèse de départ": _itv_str(itv, "plan_hypothesis"),
        "DO - Catégorie Cause Racine": _itv_str(itv, "root_cause_category"),
        "DO - Description Cause Racine": _itv_str(itv, "root_cause_description"),
        "DO - Rapport d'intervention": _itv_str(itv, "actions_performed"),
        "DO - Pièces Remplacées": consumed_summary or _itv_str(itv, "legacy_parts_text"),
        "DO - Outils Utilisés": _itv_str(itv, "tools_used"),
        "CHECK - Problème Résolu?": "OUI" if _itv_str(itv, "check_resolved", False) else "NON",
        "CHECK - Méthode de Vérification": _itv_str(itv, "check_verification_method"),
        "ACT - Actions Préventives": _itv_str(itv, "act_preventive_actions"),
        "ACT - Recommandations": _itv_str(itv, "act_recommendations"),
    }


@router.get(
    "",
    responses={
        403: {"description": "Forbidden: ChefTech only"},
        500: {"description": "Internal server error"},
    },
)
async def list_cheftech_work_orders(
    *, page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 10,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List all Work Orders assigned to technicians (for ChefTech monitoring)"""
    _require_cheftech(current_user)

    try:
        skip = (page - 1) * size

        # Count total
        count_query = select(func.count(OrdresTravail.id)).where(
            OrdresTravail.archived_at.is_(None)
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Get all WOs assigned to technicians
        query = (
            select(
                OrdresTravail,
                Machines.nom.label("machine_nom"),
                Utilisateurs.nom.label("technicien_nom"),
                Utilisateurs.email.label("technicien_email"),
                OrdresIntervention,
            )
            .outerjoin(Machines, OrdresTravail.machine_id == Machines.id)
            .outerjoin(
                OrdresIntervention,
                OrdresTravail.id == OrdresIntervention.ordre_travail_id,
            )
            .outerjoin(
                Utilisateurs, OrdresIntervention.technician_id == Utilisateurs.id
            )
            .where(OrdresTravail.archived_at.is_(None))
            .order_by(OrdresTravail.created_at.desc())
            .offset(skip)
            .limit(size)
        )

        # nosemgrep: python.fastapi.db.generic-sql-fastapi -- `query` is a SQLAlchemy
        # Core select() built entirely from ORM column expressions/joins above; no
        # string interpolation or raw SQL is involved, so there is no injectable text.
        result = await db.execute(query)
        rows = result.all()

        now = datetime.now(timezone.utc)
        output = [_build_wo_row(wo, m_nom, u_nom, u_email, itv, now) for wo, m_nom, u_nom, u_email, itv in rows]

        return PaginatedResponse.create(items=output, total=total, page=page, size=size)

    except Exception as e:
        logger.exception(f"Error listing cheftech work orders: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/{order_id}/export",
    responses={
        403: {"description": "Forbidden: ChefTech only"},
        404: {"description": "Work order not found"},
        500: {"description": "Internal server error"},
    },
)
async def export_cheftech_work_order_report(
    order_id: int,
    current_user: Annotated[Utilisateurs, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Export a complete Work Order report to Excel (horizontal format)"""
    _require_cheftech(current_user)

    try:
        query = (
            select(
                OrdresTravail,
                Machines.nom.label("machine_nom"),
                Utilisateurs.nom.label("technicien_nom"),
                Utilisateurs.email.label("technicien_email"),
                OrdresIntervention,
            )
            .outerjoin(Machines, OrdresTravail.machine_id == Machines.id)
            .outerjoin(
                OrdresIntervention,
                OrdresTravail.id == OrdresIntervention.ordre_travail_id,
            )
            .outerjoin(
                Utilisateurs, OrdresIntervention.technician_id == Utilisateurs.id
            )
            .where(OrdresTravail.id == order_id)
        )

        result = await db.execute(query)
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="Work order not found")

        wo, m_nom, u_nom, u_email, itv = row
        consumed_summary = await _fetch_consumed_summary(db, itv)
        duration_min = (
            int((wo.date_fin - wo.date_debut).total_seconds() / 60)
            if wo.date_fin and wo.date_debut
            else "N/A"
        )

        flat_row = _build_export_flat_row(wo, m_nom, u_nom, u_email, itv, consumed_summary, duration_min)
        df = pd.DataFrame([flat_row])

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Rapport Intervention", index=False)
            _autofit_columns(writer.sheets["Rapport Intervention"])

        output.seek(0)
        filename = f"Rapport_OT_{order_id}_{datetime.now().strftime('%Y%m%d')}.xlsx"

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error exporting cheftech work order report: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
