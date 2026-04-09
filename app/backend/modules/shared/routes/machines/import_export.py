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
    generate_machine_name
)

router = APIRouter(prefix="/api/v1/entities/machines", tags=["machines"])
logger = logging.getLogger(__name__)


@router.get("/import/template")
async def download_import_template():
    """Download a template for mass importing machines"""
    logger.debug("Generating machines import template")
    try:
        columns = ["nom (laisser vide pour auto-génération)", "type", "emplacement", "zone", "sous_zone", "ordre", "statut"]
        df = pd.DataFrame(columns=columns)
        
        sample_row = {
            "nom (laisser vide pour auto-génération)": "", 
            "type": "CMS", 
            "emplacement": "Atelier 1", 
            "zone": "ZONE CMS1 - COMPONENT SURFACE MOUNTING", 
            "sous_zone": "CMS LINE 1 (e.g., BBS - Broadband Products)", 
            "ordre": "1", 
            "statut": "OPERATIONNELLE"
        }
        df.loc[0] = sample_row
        
        guide_data = [
            {"Règle": "Champ 'nom'", "Description": "Optionnel. Sera généré automatiquement (ex: ZONE_CMS1_CMS_LINE_1_DEPILEUR) si la zone, sous_zone et ordre sont valides."},
            {"Règle": "Champ 'zone'", "Description": "Obligatoire. Doit correspondre EXACTEMENT à une des valeurs autorisées."},
            {"Règle": "Champ 'sous_zone'", "Description": "Obligatoire. Doit correspondre EXACTEMENT à une sous-zone liée à la zone choisie."},
            {"Règle": "Champ 'ordre'", "Description": "Obligatoire. Un chiffre correspondant à l'ordre de la machine (ex: 1, 2, 3)."},
            {"Règle": "Zones Autorisées", "Description": " | ".join(ZONE_OPTIONS)},
        ]
        
        for zone, sub_zones in SOUS_ZONE_OPTIONS_BY_ZONE.items():
            if sub_zones:
                guide_data.append({"Règle": f"Sous-zones pour: {zone}", "Description": " | ".join(sub_zones)})
                
        for zone, sub_zones in ORDRE_TEMPLATES.items():
            for sub, templates in sub_zones.items():
                items = [f"{t['ordre']}={t['nom']}" for t in templates]
                guide_data.append({"Règle": f"Ordres pour: {sub}", "Description": " | ".join(items)})
                
        df_guide = pd.DataFrame(guide_data)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Machines')
            df_guide.to_excel(writer, index=False, sheet_name='Guide des Règles')
            
            worksheet = writer.sheets['Machines']
            for i, col in enumerate(df.columns):
                column_width = max(df[col].astype(str).map(len).max(), len(col)) + 5
                worksheet.column_dimensions[chr(65+i)].width = column_width

        output.seek(0)
        
        headers = {
            'Content-Disposition': 'attachment; filename="machines_import_template.xlsx"'
        }
        return StreamingResponse(
            output, 
            headers=headers,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        logger.error(f"Error generating template: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating template: {str(e)}")


@router.post("/import/preview")
async def preview_machine_import(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Parse an uploaded file (CSV or Excel) and validate its contents for machines import"""
    logger.debug(f"Previewing import file: {file.filename}")
    
    if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Invalid file format. Only CSV and Excel files are supported.")
        
    try:
        contents = await file.read()
        
        if file.filename.endswith('.csv'):
            try:
                df = pd.read_csv(io.BytesIO(contents), sep=None, engine='python')
            except Exception:
                df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
            
        df.columns = df.columns.str.strip().str.lower()
        if hasattr(df, 'map'):
            df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        else:
            df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
        df = df.where(pd.notnull(df), None)
        
        results = []
        
        stmt = select(Machines.nom)
        db_result = await db.execute(stmt)
        existing_names = set([row[0] for row in db_result.all()])
        
        file_names_seen = set()
        
        for index, row_data in df.iterrows():
            row_dict = row_data.to_dict()
            
            raw_nom = None
            for key in row_dict.keys():
                if 'nom' in key.lower():
                    raw_nom = str(row_dict[key]).strip() if pd.notnull(row_dict[key]) and str(row_dict[key]).strip() else None
                    break
                    
            r_zone = str(row_dict.get('zone', '')).strip() if pd.notnull(row_dict.get('zone')) else ''
            r_sous_zone = str(row_dict.get('sous_zone', '')).strip() if pd.notnull(row_dict.get('sous_zone')) else ''
            r_ordre = str(row_dict.get('ordre', '')).replace('.0', '').strip() if pd.notnull(row_dict.get('ordre')) else ''
            r_statut = str(row_dict.get('statut', '')).strip() if pd.notnull(row_dict.get('statut')) else ''
            if not r_statut:
                r_statut = 'OPERATIONNELLE'
                
            errors = []
            warnings = []
            valid = True
            
            if not r_zone:
                errors.append("La 'zone' est obligatoire.")
                valid = False
            elif r_zone not in ZONE_OPTIONS:
                errors.append(f"La zone '{r_zone}' est invalide. Choisissez parmi les zones définies dans le guide.")
                valid = False
                
            if r_zone in ZONE_OPTIONS:
                allowed_sous_zones = SOUS_ZONE_OPTIONS_BY_ZONE.get(r_zone, [])
                if allowed_sous_zones:
                    if not r_sous_zone:
                        errors.append(f"La 'sous_zone' est obligatoire pour {r_zone}.")
                        valid = False
                    elif r_sous_zone not in allowed_sous_zones:
                        errors.append(f"La sous_zone '{r_sous_zone}' est invalide pour {r_zone}. Options: {', '.join(allowed_sous_zones)}")
                        valid = False
                        
                if r_sous_zone in allowed_sous_zones or not allowed_sous_zones:
                    templates_list = ORDRE_TEMPLATES.get(r_zone, {}).get(r_sous_zone, [])
                    if templates_list:
                        if not r_ordre:
                            errors.append(f"L' 'ordre' est obligatoire pour identifier la machine. Options: {[str(t['ordre']) for t in templates_list]}")
                            valid = False
                        else:
                            try:
                                r_ordre_int = int(r_ordre)
                                if not any(t['ordre'] == r_ordre_int for t in templates_list):
                                    errors.append(f"L'ordre '{r_ordre}' n'existe pas pour {r_sous_zone}.")
                                    valid = False
                            except ValueError:
                                errors.append(f"L'ordre doit être un nombre valide.")
                                valid = False
                                
            if r_statut and r_statut not in MACHINE_STATUS_OPTIONS:
                errors.append(f"Statut '{r_statut}' invalide. Options: {', '.join(MACHINE_STATUS_OPTIONS)}")
                valid = False
            
            final_name = raw_nom
            if valid:
                generated_name = generate_machine_name(r_zone, r_sous_zone, r_ordre)
                if not raw_nom:
                    final_name = generated_name
                elif raw_nom != generated_name and generated_name:
                    warnings.append(f"Le nom '{raw_nom}' a été remplacé par le nom standard '{generated_name}'.")
                    final_name = generated_name
            
            if not final_name and valid:
                errors.append("Le système n'a pas pu générer un nom de machine (manque de données).")
                valid = False
                
            if final_name and valid:
                if final_name in existing_names:
                    errors.append(f"La machine '{final_name}' existe déjà en base de données.")
                    valid = False
                if final_name in file_names_seen:
                    errors.append(f"Le nom '{final_name}' apparaît plusieurs fois dans ce fichier (vérifiez vos zones et ordres).")
                    valid = False
                else:
                    file_names_seen.add(final_name)
            
            clean_row = {
                "nom": final_name if final_name else (raw_nom or ''),
                "type": row_dict.get('type') if pd.notnull(row_dict.get('type')) else '',
                "emplacement": row_dict.get('emplacement') if pd.notnull(row_dict.get('emplacement')) else '',
                "zone": r_zone,
                "sous_zone": r_sous_zone,
                "ordre": r_ordre,
                "statut": r_statut
            }
            
            results.append({
                "row_index": index + 2,
                "data": clean_row,
                "valid": valid,
                "errors": errors,
                "warnings": warnings
            })
            
        stats = {
            "total": len(results),
            "valid": len([r for r in results if r["valid"]]),
            "invalid": len([r for r in results if not r["valid"]])
        }
            
        return {"stats": stats, "items": results}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error parsing import file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error parsing file: {str(e)}")
