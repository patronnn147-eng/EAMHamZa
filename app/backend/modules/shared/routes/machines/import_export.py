import io
import logging
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from models.machines import Machines
from modules.shared.admin_machine_standards import (
    ZONE_OPTIONS,
    SOUS_ZONE_OPTIONS_BY_ZONE,
    ORDRE_TEMPLATES,
    MACHINE_STATUS_OPTIONS,
    generate_machine_name,
)
from typing import Annotated

router = APIRouter(prefix="/api/v1/entities/machines", tags=["machines"])
logger = logging.getLogger(__name__)

RULE_COLUMN = "Règle"


def _read_dataframe(contents: bytes, filename: str) -> pd.DataFrame:
    """Parse file bytes into a DataFrame (CSV or Excel)."""
    if filename.endswith(".csv"):
        try:
            return pd.read_csv(io.BytesIO(contents), sep=None, engine="python")
        except Exception:
            return pd.read_csv(io.BytesIO(contents))
    return pd.read_excel(io.BytesIO(contents))


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise column names, strip whitespace, replace NaN with None."""
    df.columns = df.columns.str.strip().str.lower()
    strip_fn = lambda x: x.strip() if isinstance(x, str) else x
    if hasattr(df, "map"):
        df = df.map(strip_fn)
    else:
        df = df.applymap(strip_fn)
    return df.where(pd.notnull(df), None)


def _extract_row_fields(row_dict: dict) -> tuple:
    """Extract and normalise the five key fields from a row dict."""
    raw_nom = None
    for key in row_dict:
        if "nom" in key.lower():
            val = row_dict[key]
            raw_nom = str(val).strip() if pd.notnull(val) and str(val).strip() else None
            break

    def _safe_str(key, default=""):
        v = row_dict.get(key)
        return str(v).strip() if pd.notnull(v) else default

    r_zone = _safe_str("zone")
    r_sous_zone = _safe_str("sous_zone")
    r_ordre = _safe_str("ordre").replace(".0", "").strip()
    r_statut = _safe_str("statut") or "OPERATIONNELLE"
    return raw_nom, r_zone, r_sous_zone, r_ordre, r_statut


def _validate_zone_and_sous_zone(r_zone: str, r_sous_zone: str, errors: list) -> bool:
    """Validate zone/sous_zone; returns False if invalid."""
    if not r_zone:
        errors.append("La 'zone' est obligatoire.")
        return False
    if r_zone not in ZONE_OPTIONS:
        errors.append(
            f"La zone '{r_zone}' est invalide. Choisissez parmi les zones définies dans le guide."
        )
        return False
    allowed_sous_zones = SOUS_ZONE_OPTIONS_BY_ZONE.get(r_zone, [])
    if not allowed_sous_zones:
        return True
    if not r_sous_zone:
        errors.append(f"La 'sous_zone' est obligatoire pour {r_zone}.")
        return False
    if r_sous_zone not in allowed_sous_zones:
        errors.append(
            f"La sous_zone '{r_sous_zone}' est invalide pour {r_zone}. Options: {', '.join(allowed_sous_zones)}"
        )
        return False
    return True


def _validate_ordre(r_zone: str, r_sous_zone: str, r_ordre: str, errors: list) -> bool:
    """Validate the ordre field against known templates; returns False if invalid."""
    templates_list = ORDRE_TEMPLATES.get(r_zone, {}).get(r_sous_zone, [])
    if not templates_list:
        return True
    if not r_ordre:
        options = [str(t["ordre"]) for t in templates_list]
        errors.append(
            f"L' 'ordre' est obligatoire pour identifier la machine. Options: {options}"
        )
        return False
    try:
        r_ordre_int = int(r_ordre)
    except ValueError:
        errors.append("L'ordre doit être un nombre valide.")
        return False
    if not any(t["ordre"] == r_ordre_int for t in templates_list):
        errors.append(f"L'ordre '{r_ordre}' n'existe pas pour {r_sous_zone}.")
        return False
    return True


def _validate_row(r_zone: str, r_sous_zone: str, r_ordre: str, r_statut: str) -> tuple:
    """Run all field validations; return (valid, errors)."""
    errors = []
    zone_ok = _validate_zone_and_sous_zone(r_zone, r_sous_zone, errors)
    if zone_ok:
        allowed_sous_zones = SOUS_ZONE_OPTIONS_BY_ZONE.get(r_zone, [])
        if r_sous_zone in allowed_sous_zones or not allowed_sous_zones:
            if not _validate_ordre(r_zone, r_sous_zone, r_ordre, errors):
                zone_ok = False
    if r_statut and r_statut not in MACHINE_STATUS_OPTIONS:
        errors.append(
            f"Statut '{r_statut}' invalide. Options: {', '.join(MACHINE_STATUS_OPTIONS)}"
        )
        zone_ok = False
    return (len(errors) == 0), errors


def _resolve_name(
    raw_nom, r_zone: str, r_sous_zone: str, r_ordre: str, valid: bool
) -> tuple:
    """Generate/standardise name; return (final_name, warnings, valid, errors)."""
    warnings = []
    errors = []
    if not valid:
        return raw_nom, warnings, valid, errors
    generated_name = generate_machine_name(r_zone, r_sous_zone, r_ordre)
    if not raw_nom:
        final_name = generated_name
    elif raw_nom != generated_name and generated_name:
        warnings.append(
            f"Le nom '{raw_nom}' a été remplacé par le nom standard '{generated_name}'."
        )
        final_name = generated_name
    else:
        final_name = raw_nom
    if not final_name:
        errors.append("Le système n'a pas pu générer un nom de machine (manque de données).")
        return final_name, warnings, False, errors
    return final_name, warnings, valid, errors


def _check_name_uniqueness(
    final_name, valid: bool, existing_names: set, file_names_seen: set, errors: list
) -> bool:
    """Check DB and intra-file name uniqueness; returns updated valid flag."""
    if not final_name or not valid:
        return valid
    if final_name in existing_names:
        errors.append(f"La machine '{final_name}' existe déjà en base de données.")
        return False
    if final_name in file_names_seen:
        errors.append(
            f"Le nom '{final_name}' apparaît plusieurs fois dans ce fichier (vérifiez vos zones et ordres)."
        )
        return False
    file_names_seen.add(final_name)
    return valid


def _process_row(index, row_data, existing_names: set, file_names_seen: set) -> dict:
    """Validate and transform a single DataFrame row into a result dict."""
    row_dict = row_data.to_dict()
    raw_nom, r_zone, r_sous_zone, r_ordre, r_statut = _extract_row_fields(row_dict)
    valid, errors = _validate_row(r_zone, r_sous_zone, r_ordre, r_statut)
    final_name, warnings, valid, name_errors = _resolve_name(
        raw_nom, r_zone, r_sous_zone, r_ordre, valid
    )
    errors.extend(name_errors)
    valid = _check_name_uniqueness(final_name, valid, existing_names, file_names_seen, errors)
    clean_row = {
        "nom": final_name if final_name else (raw_nom or ""),
        "type": row_dict.get("type") if pd.notnull(row_dict.get("type")) else "",
        "emplacement": row_dict.get("emplacement") if pd.notnull(row_dict.get("emplacement")) else "",
        "zone": r_zone,
        "sous_zone": r_sous_zone,
        "ordre": r_ordre,
        "statut": r_statut,
    }
    return {"row_index": index + 2, "data": clean_row, "valid": valid, "errors": errors, "warnings": warnings}


@router.get("/import/template", responses={500: {"description": "Internal Server Error"}})
async def download_import_template():
    """Download a template for mass importing machines"""
    logger.debug("Generating machines import template")
    try:
        columns = [
            "nom (laisser vide pour auto-génération)",
            "type",
            "emplacement",
            "zone",
            "sous_zone",
            "ordre",
            "statut",
        ]
        df = pd.DataFrame(columns=columns)

        sample_row = {
            "nom (laisser vide pour auto-génération)": "",
            "type": "CMS",
            "emplacement": "Atelier 1",
            "zone": "ZONE CMS1 - COMPONENT SURFACE MOUNTING",
            "sous_zone": "CMS LINE 1 (e.g., BBS - Broadband Products)",
            "ordre": "1",
            "statut": "OPERATIONNELLE",
        }
        df.loc[0] = sample_row

        guide_data = [
            {
                RULE_COLUMN: "Champ 'nom'",
                "Description": "Optionnel. Sera généré automatiquement (ex: ZONE_CMS1_CMS_LINE_1_DEPILEUR) si la zone, sous_zone et ordre sont valides.",
            },
            {
                RULE_COLUMN: "Champ 'zone'",
                "Description": "Obligatoire. Doit correspondre EXACTEMENT à une des valeurs autorisées.",
            },
            {
                RULE_COLUMN: "Champ 'sous_zone'",
                "Description": "Obligatoire. Doit correspondre EXACTEMENT à une sous-zone liée à la zone choisie.",
            },
            {
                RULE_COLUMN: "Champ 'ordre'",
                "Description": "Obligatoire. Un chiffre correspondant à l'ordre de la machine (ex: 1, 2, 3).",
            },
            {RULE_COLUMN: "Zones Autorisées", "Description": " | ".join(ZONE_OPTIONS)},
        ]

        for zone, sub_zones in SOUS_ZONE_OPTIONS_BY_ZONE.items():
            if sub_zones:
                guide_data.append(
                    {
                        RULE_COLUMN: f"Sous-zones pour: {zone}",
                        "Description": " | ".join(sub_zones),
                    }
                )

        for zone, sub_zones in ORDRE_TEMPLATES.items():
            for sub, templates in sub_zones.items():
                items = [f"{t['ordre']}={t['nom']}" for t in templates]
                guide_data.append(
                    {RULE_COLUMN: f"Ordres pour: {sub}", "Description": " | ".join(items)}
                )

        df_guide = pd.DataFrame(guide_data)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Machines")
            df_guide.to_excel(writer, index=False, sheet_name="Guide des Règles")

            worksheet = writer.sheets["Machines"]
            for i, col in enumerate(df.columns):
                column_width = max(df[col].astype(str).map(len).max(), len(col)) + 5
                worksheet.column_dimensions[chr(65 + i)].width = column_width

        output.seek(0)

        headers = {
            "Content-Disposition": 'attachment; filename="machines_import_template.xlsx"'
        }
        return StreamingResponse(
            output,
            headers=headers,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        logger.exception(f"Error generating template: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error generating template: {str(e)}"
        )


@router.post("/import/preview", responses={400: {"description": "Invalid file format. Only CSV and Excel files are supported."}, 500: {"description": "Internal Server Error"}})
async def preview_machine_import(
    file: Annotated[UploadFile, File()], db: Annotated[AsyncSession, Depends(get_db)]
):
    """Parse an uploaded file (CSV or Excel) and validate its contents for machines import"""
    logger.debug(f"Previewing import file: {file.filename}")

    if not file.filename.endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only CSV and Excel files are supported.",
        )

    try:
        contents = await file.read()
        df = _clean_dataframe(_read_dataframe(contents, file.filename))

        db_result = await db.execute(select(Machines.nom))
        existing_names = {row[0] for row in db_result.all()}
        file_names_seen: set = set()

        results = [
            _process_row(index, row_data, existing_names, file_names_seen)
            for index, row_data in df.iterrows()
        ]

        stats = {
            "total": len(results),
            "valid": sum(1 for r in results if r["valid"]),
            "invalid": sum(1 for r in results if not r["valid"]),
        }
        return {"stats": stats, "items": results}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error parsing import file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error parsing file: {str(e)}")
