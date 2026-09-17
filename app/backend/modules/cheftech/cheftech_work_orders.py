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
from models.ordres_travail import Ordres_travail
from models.machines import Machines
from models.ordres_intervention import Ordres_intervention
from typing import Annotated

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/cheftech/work-orders-table", tags=["cheftech-work-orders"]
)


def _require_cheftech(current_user: Utilisateurs):
    if current_user.role not in [UserRole.CHEFTECH, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Forbidden: ChefTech only")


@router.get("", responses={500: {"description": "Internal server error"}})
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
        count_query = select(func.count(Ordres_travail.id)).where(
            Ordres_travail.archived_at.is_(None)
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Get all WOs assigned to technicians
        query = (
            select(
                Ordres_travail,
                Machines.nom.label("machine_nom"),
                Utilisateurs.nom.label("technicien_nom"),
                Utilisateurs.email.label("technicien_email"),
                Ordres_intervention,
            )
            .outerjoin(Machines, Ordres_travail.machine_id == Machines.id)
            .outerjoin(
                Ordres_intervention,
                Ordres_travail.id == Ordres_intervention.ordre_travail_id,
            )
            .outerjoin(
                Utilisateurs, Ordres_intervention.technician_id == Utilisateurs.id
            )
            .where(Ordres_travail.archived_at.is_(None))
            .order_by(Ordres_travail.created_at.desc())
            .offset(skip)
            .limit(size)
        )

        # nosemgrep: python.fastapi.db.generic-sql-fastapi -- `query` is a SQLAlchemy
        # Core select() built entirely from ORM column expressions/joins above; no
        # string interpolation or raw SQL is involved, so there is no injectable text.
        result = await db.execute(query)
        rows = result.all()

        output = []
        now = datetime.now(timezone.utc)

        for wo, m_nom, u_nom, u_email, itv in rows:
            # Calculate live duration
            if wo.date_fin and wo.date_debut:
                duration_min = int((wo.date_fin - wo.date_debut).total_seconds() / 60)
                live_seconds = None
            elif wo.date_debut:
                duration_min = None
                live_seconds = int(
                    (now - wo.date_debut.replace(tzinfo=None)).total_seconds()
                )
            else:
                duration_min = None
                live_seconds = None

            output.append(
                {
                    "id": wo.id,
                    "titre": wo.titre,
                    "machine_nom": m_nom or "N/A",
                    "technicien_id": itv.technician_id if itv else None,
                    "technicien_nom": u_nom or "N/A",
                    "technicien_email": u_email or "N/A",
                    "intervention_id": itv.id if itv else None,
                    "statut": wo.statut,
                    "priorite": wo.priorite,
                    "created_at": wo.created_at.isoformat() if wo.created_at else None,
                    "date_debut": wo.date_debut.isoformat() if wo.date_debut else None,
                    "date_fin": wo.date_fin.isoformat() if wo.date_fin else None,
                    "duration_min": duration_min,
                    "live_seconds": live_seconds,
                    "rapport": wo.rapport,
                    # PDCA
                    "intervention_type": getattr(itv, "intervention_type", None)
                    if itv
                    else None,
                    "machine_status_after": getattr(itv, "machine_status_after", None)
                    if itv
                    else None,
                    "plan_hypothesis": getattr(itv, "plan_hypothesis", None)
                    if itv
                    else None,
                    "root_cause_category": getattr(itv, "root_cause_category", None)
                    if itv
                    else None,
                    "root_cause_description": getattr(
                        itv, "root_cause_description", None
                    )
                    if itv
                    else None,
                    "actions_performed": getattr(itv, "actions_performed", None)
                    if itv
                    else None,
                    "parts_replaced": (
                        getattr(itv, "legacy_parts_text", None) if itv else None
                    ),
                    "tools_used": getattr(itv, "tools_used", None) if itv else None,
                    "check_resolved": getattr(itv, "check_resolved", None)
                    if itv
                    else None,
                    "check_verification_method": getattr(
                        itv, "check_verification_method", None
                    )
                    if itv
                    else None,
                    "act_preventive_actions": getattr(
                        itv, "act_preventive_actions", None
                    )
                    if itv
                    else None,
                    "act_recommendations": getattr(itv, "act_recommendations", None)
                    if itv
                    else None,
                }
            )

        return PaginatedResponse.create(items=output, total=total, page=page, size=size)

    except Exception as e:
        logger.exception(f"Error listing cheftech work orders: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{order_id}/export", responses={404: {"description": "Work order not found"}, 500: {"description": "Internal server error"}})
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
                Ordres_travail,
                Machines.nom.label("machine_nom"),
                Utilisateurs.nom.label("technicien_nom"),
                Utilisateurs.email.label("technicien_email"),
                Ordres_intervention,
            )
            .outerjoin(Machines, Ordres_travail.machine_id == Machines.id)
            .outerjoin(
                Ordres_intervention,
                Ordres_travail.id == Ordres_intervention.ordre_travail_id,
            )
            .outerjoin(
                Utilisateurs, Ordres_intervention.technician_id == Utilisateurs.id
            )
            .where(Ordres_travail.id == order_id)
        )

        result = await db.execute(query)
        row = result.first()

        if not row:
            raise HTTPException(status_code=404, detail="Work order not found")

        wo, m_nom, u_nom, u_email, itv = row

        def itv_get(attr, default="N/A"):
            return getattr(itv, attr, None) or default if itv else default

        # Fetch consumed-pieces summary from the canonical VIEW
        consumed_summary = None
        if itv is not None:
            try:
                _row = (
                    await db.execute(
                        text(
                            "SELECT parts_replaced_json FROM intervention_consumption_summary WHERE intervention_id = :iid"
                        ),
                        {"iid": itv.id},
                    )
                ).first()
                if _row and _row[0]:
                    import json as _json

                    _data = (
                        _row[0] if isinstance(_row[0], list) else _json.loads(_row[0])
                    )
                    consumed_summary = ", ".join(
                        f"{x.get('piece_name', '?')} ({x.get('used', '0')}{x.get('unit', '')}"
                        + (
                            f", retour={x.get('returned', '0')}"
                            if float(x.get("returned", 0) or 0)
                            else ""
                        )
                        + (
                            f", rebut={x.get('wasted', '0')}"
                            if float(x.get("wasted", 0) or 0)
                            else ""
                        )
                        + ")"
                        for x in _data
                    )
            except Exception:
                pass

        duration_min = "N/A"
        if wo.date_fin and wo.date_debut:
            duration_min = int((wo.date_fin - wo.date_debut).total_seconds() / 60)

        flat_row = {
            # Work Order Info
            "ID OT": wo.id,
            "Titre": wo.titre or "N/A",
            "Machine": m_nom or "N/A",
            "Technicien": u_nom or "N/A",
            "Email Technicien": u_email or "N/A",
            "Date Création": wo.created_at.strftime("%Y-%m-%d %H:%M")
            if wo.created_at
            else "N/A",
            "Date Début": wo.date_debut.strftime("%Y-%m-%d %H:%M")
            if wo.date_debut
            else "N/A",
            "Date Fin": wo.date_fin.strftime("%Y-%m-%d %H:%M")
            if wo.date_fin
            else "N/A",
            "Durée (min)": duration_min,
            "Statut OT": wo.statut,
            "Priorité": wo.priorite,
            "Rapport Brut": wo.rapport or "N/A",
            # Intervention
            "ID Intervention": itv.id if itv else "N/A",
            "Priorité Intervention": itv_get("priority"),
            "Symptômes": itv_get("symptoms"),
            "Impact": itv_get("impact"),
            "Fréquence": itv_get("frequency"),
            "Score de Risque": itv_get("risk_score"),
            # PDCA
            "Type d'intervention": itv_get("intervention_type"),
            "État Machine Après": itv_get("machine_status_after"),
            "PLAN - Hypothèse de départ": itv_get("plan_hypothesis"),
            "DO - Catégorie Cause Racine": itv_get("root_cause_category"),
            "DO - Description Cause Racine": itv_get("root_cause_description"),
            "DO - Rapport d'intervention": itv_get("actions_performed"),
            "DO - Pièces Remplacées": (
                consumed_summary or itv_get("legacy_parts_text") or "N/A"
            ),
            "DO - Outils Utilisés": itv_get("tools_used"),
            "CHECK - Problème Résolu?": "OUI"
            if itv_get("check_resolved", False)
            else "NON",
            "CHECK - Méthode de Vérification": itv_get("check_verification_method"),
            "ACT - Actions Préventives": itv_get("act_preventive_actions"),
            "ACT - Recommandations": itv_get("act_recommendations"),
        }

        df = pd.DataFrame([flat_row])

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Rapport Intervention", index=False)
            worksheet = writer.sheets["Rapport Intervention"]
            for col_cells in worksheet.columns:
                max_length = max(
                    (len(str(cell.value)) for cell in col_cells if cell.value),
                    default=0,
                )
                col_letter = col_cells[0].column_letter
                worksheet.column_dimensions[col_letter].width = min(max_length + 4, 60)

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
