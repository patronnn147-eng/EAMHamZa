from datetime import datetime
import io
import logging

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from schemas.pagination import PaginatedResponse

from core.database import get_db
from core.auth import get_current_user
from models.utilisateurs import Utilisateurs, UserRole
from models.ordres_travail import Ordres_travail
from models.machines import Machines
from models.ordres_intervention import Ordres_intervention

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/work-orders", tags=["admin-work-orders"])


@router.get("")
async def list_work_orders(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all work orders with ChefOp and Machine details for Admin"""
    try:
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Forbidden: Admin only")

        skip = (page - 1) * size

        # Base query structure for both count and select
        select(Ordres_travail).where(Ordres_travail.archived_at.is_(None)).outerjoin(
            Machines, Ordres_travail.machine_id == Machines.id
        ).outerjoin(
            Ordres_intervention,
            Ordres_travail.id == Ordres_intervention.ordre_travail_id,
        ).outerjoin(Utilisateurs, Ordres_travail.created_by == Utilisateurs.id)

        # Count total
        total_result = await db.execute(
            select(func.count(Ordres_travail.id)).where(
                Ordres_travail.archived_at.is_(None)
            )
        )
        total = total_result.scalar() or 0

        # Detailed query with pagination
        query = (
            select(
                Ordres_travail,
                Machines.nom.label("machine_nom"),
                Utilisateurs.nom.label("chefop_nom"),
                Utilisateurs.email.label("chefop_email"),
                Ordres_intervention.id.label("intervention_id"),
            )
            .outerjoin(Machines, Ordres_travail.machine_id == Machines.id)
            .outerjoin(
                Ordres_intervention,
                Ordres_travail.id == Ordres_intervention.ordre_travail_id,
            )
            .outerjoin(Utilisateurs, Ordres_travail.created_by == Utilisateurs.id)
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
        for wo, m_nom, u_nom, u_email, itv_id in rows:
            # Calculate duration
            duration_minutes = 0
            if wo.date_debut and wo.date_fin:
                diff = wo.date_fin - wo.date_debut
                duration_minutes = int(diff.total_seconds() / 60)
            elif wo.date_debut and wo.statut == "EN_COURS":
                diff = datetime.utcnow() - wo.date_debut
                duration_minutes = int(diff.total_seconds() / 60)

            output.append(
                {
                    "id": wo.id,
                    "titre": wo.titre,
                    "description": wo.description,
                    "priorite": wo.priorite,
                    "statut": wo.statut,
                    "machine_id": wo.machine_id,
                    "machine_nom": m_nom or "N/A",
                    "chefop_id": wo.utilisateur_id or 0,
                    "chefop_nom": u_nom or "N/A",
                    "chefop_email": u_email or "N/A",
                    "intervention_id": itv_id,
                    "created_at": wo.created_at,
                    "date_debut": wo.date_debut,
                    "date_fin": wo.date_fin,
                    "duration_minutes": duration_minutes,
                }
            )

        return PaginatedResponse.create(items=output, total=total, page=page, size=size)
    except Exception as e:
        logger.error(f"Error listing admin work orders: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{order_id}/export")
async def export_work_order_report(
    order_id: int,
    current_user: Utilisateurs = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export a complete Work Order report to Excel (horizontal format, analysis-ready)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden: Admin only")

    try:
        # Fetch WO with all related data
        query = (
            select(
                Ordres_travail,
                Machines.nom.label("machine_nom"),
                Utilisateurs.nom.label("chefop_nom"),
                Utilisateurs.email.label("chefop_email"),
                Ordres_intervention,
            )
            .outerjoin(Machines, Ordres_travail.machine_id == Machines.id)
            .outerjoin(
                Ordres_intervention,
                Ordres_travail.id == Ordres_intervention.ordre_travail_id,
            )
            .outerjoin(Utilisateurs, Ordres_travail.created_by == Utilisateurs.id)
            .where(Ordres_travail.id == order_id)
        )

        result = await db.execute(query)
        row = result.first()

        if not row:
            raise HTTPException(status_code=404, detail="Work order not found")

        wo, m_nom, u_nom, u_email, itv = row

        # Helper to safely read intervention attribute
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
                logger.debug(
                    "intervention_consumption_summary view read failed", exc_info=True
                )

        # Duration
        duration_min = "N/A"
        if wo.date_fin and wo.date_debut:
            duration_min = int((wo.date_fin - wo.date_debut).total_seconds() / 60)

        # ---  Single flat row (horizontal layout) ---
        flat_row = {
            # === Work Order Info ===
            "ID OT": wo.id,
            "Titre": wo.titre or "N/A",
            "Machine": m_nom or "N/A",
            "Chef Opérateur": u_nom or "N/A",
            "Email ChefOp": u_email or "N/A",
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
            "Rapport Brut": wo.rapport or "N/A",
            # === Intervention & DI ===
            "ID Intervention": itv.id if itv else "N/A",
            "Priorité": itv_get("priority"),
            "Symptômes": itv_get("symptoms"),
            "Impact": itv_get("impact"),
            "Fréquence": itv_get("frequency"),
            "Score de Risque": itv_get("risk_score"),
            # === Details Intervention & PDCA ===
            "Type d'intervention": itv_get("intervention_type"),
            "État Machine Après": itv_get("machine_status_after"),
            # --- PLAN ---
            "PLAN - Hypothèse de départ": itv_get("plan_hypothesis"),
            # --- DO ---
            "DO - Catégorie Cause Racine": itv_get("root_cause_category"),
            "DO - Description Cause Racine": itv_get("root_cause_description"),
            "DO - Rapport d'intervention": itv_get("actions_performed"),
            "DO - Pièces Remplacées": (
                consumed_summary or itv_get("legacy_parts_text") or "N/A"
            ),
            "DO - Outils Utilisés": itv_get("tools_used"),
            # --- CHECK ---
            "CHECK - Problème Résolu?": "OUI"
            if itv_get("check_resolved", False)
            else "NON",
            "CHECK - Méthode de Vérification": itv_get("check_verification_method"),
            # --- ACT ---
            "ACT - Actions Préventives": itv_get("act_preventive_actions"),
            "ACT - Recommandations": itv_get("act_recommendations"),
        }

        # Build single-row DataFrame
        df = pd.DataFrame([flat_row])

        # Generate Excel in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Rapport Intervention", index=False)

            # Auto-adjust column widths
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
        logger.error(f"Error exporting work order report: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
