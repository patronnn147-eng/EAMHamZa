import json
import logging
import io
import pandas as pd
from typing import List, Optional

from datetime import datetime, date

from fastapi import APIRouter, Body, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from models.machines import Machines
from services.machines import MachinesService
from modules.shared.admin_machine_standards import (
    ZONE_OPTIONS,
    SOUS_ZONE_OPTIONS_BY_ZONE,
    ORDRE_TEMPLATES,
    MACHINE_STATUS_OPTIONS,
    generate_machine_name
)

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/machines", tags=["machines"])


# ---------- Pydantic Schemas ----------
class MachinesData(BaseModel):
    """Entity data schema (for create/update)"""
    nom: str
    zone: Optional[str] = None
    sous_zone: Optional[str] = None
    ordre: Optional[str] = None
    date_derniere_maintenance: Optional[datetime] = None
    date_prochaine_maintenance: Optional[datetime] = None
    image_url: Optional[str] = None
    created_at: Optional[datetime] = None


class MachinesUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    nom: Optional[str] = None
    zone: Optional[str] = None
    sous_zone: Optional[str] = None
    ordre: Optional[str] = None
    date_derniere_maintenance: Optional[datetime] = None
    date_prochaine_maintenance: Optional[datetime] = None
    image_url: Optional[str] = None
    created_at: Optional[datetime] = None


class MachinesResponse(BaseModel):
    """Entity response schema"""
    id: int
    nom: str
    zone: Optional[str] = None
    sous_zone: Optional[str] = None
    ordre: Optional[str] = None
    date_derniere_maintenance: Optional[datetime] = None
    date_prochaine_maintenance: Optional[datetime] = None
    image_url: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MachinesListResponse(BaseModel):
    """List response schema"""
    items: List[MachinesResponse]
    total: int
    skip: int
    limit: int


class MachinesBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[MachinesData]


class MachinesBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: MachinesUpdateData


class MachinesBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[MachinesBatchUpdateItem]


class MachinesBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=MachinesListResponse)
async def query_machiness(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query machiness with filtering, sorting, and pagination"""
    logger.debug(f"Querying machiness: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = MachinesService(db)
    try:
        # Parse query JSON if provided
        query_dict = None
        if query:
            try:
                query_dict = json.loads(query)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid query JSON format")
        
        result = await service.get_list(
            skip=skip, 
            limit=limit,
            query_dict=query_dict,
            sort=sort,
        )
        logger.debug(f"Found {result['total']} machiness")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying machiness: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=MachinesListResponse)
async def query_machiness_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query machiness with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying machiness: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = MachinesService(db)
    try:
        # Parse query JSON if provided
        query_dict = None
        if query:
            try:
                query_dict = json.loads(query)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid query JSON format")

        result = await service.get_list(
            skip=skip,
            limit=limit,
            query_dict=query_dict,
            sort=sort
        )
        logger.debug(f"Found {result['total']} machiness")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying machiness: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=MachinesResponse)
async def get_machines(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single machines by ID"""
    logger.debug(f"Fetching machines with id: {id}, fields={fields}")
    
    service = MachinesService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Machines with id {id} not found")
            raise HTTPException(status_code=404, detail="Machines not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching machines {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=MachinesResponse, status_code=201)
async def create_machines(
    data: MachinesData,
    db: AsyncSession = Depends(get_db),
):
    """Create a new machines"""
    logger.debug(f"Creating new machines with data: {data}")
    
    service = MachinesService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create machines")
        
        logger.info(f"Machines created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating machines: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating machines: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[MachinesResponse], status_code=201)
async def create_machiness_batch(
    request: MachinesBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple machiness in a single request"""
    logger.debug(f"Batch creating {len(request.items)} machiness")
    
    service = MachinesService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} machiness successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[MachinesResponse])
async def update_machiness_batch(
    request: MachinesBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple machiness in a single request"""
    logger.debug(f"Batch updating {len(request.items)} machiness")
    
    service = MachinesService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} machiness successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=MachinesResponse)
async def update_machines(
    id: int,
    data: MachinesUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing machines"""
    logger.debug(f"Updating machines {id} with data: {data}")

    service = MachinesService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Machines with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Machines not found")
        
        logger.info(f"Machines {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating machines {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating machines {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_machiness_batch(
    request: MachinesBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple machiness by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} machiness")
    
    service = MachinesService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} machiness successfully")
        return {"message": f"Successfully deleted {deleted_count} machiness", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_machines(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single machines by ID"""
    logger.debug(f"Deleting machines with id: {id}")
    
    service = MachinesService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Machines with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Machines not found")
        
        logger.info(f"Machines {id} deleted successfully")
        return {"message": "Machines deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting machines {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/import/template")
async def download_import_template():
    """Download a template for mass importing machines"""
    logger.debug("Generating machines import template")
    try:
        # Create a DataFrame with required columns
        columns = ["nom (laisser vide pour auto-génération)", "type", "emplacement", "zone", "sous_zone", "ordre", "statut"]
        df = pd.DataFrame(columns=columns)
        
        # Add a sample row to guide the user (using valid inputs)
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
        
        # Create instructions DataFrame
        guide_data = [
            {"Règle": "Champ 'nom'", "Description": "Optionnel. Sera généré automatiquement (ex: ZONE_CMS1_CMS_LINE_1_DEPILEUR) si la zone, sous_zone et ordre sont valides."},
            {"Règle": "Champ 'zone'", "Description": "Obligatoire. Doit correspondre EXACTEMENT à une des valeurs autorisées."},
            {"Règle": "Champ 'sous_zone'", "Description": "Obligatoire. Doit correspondre EXACTEMENT à une sous-zone liée à la zone choisie."},
            {"Règle": "Champ 'ordre'", "Description": "Obligatoire. Un chiffre correspondant à l'ordre de la machine (ex: 1, 2, 3)."},
            {"Règle": "Zones Autorisées", "Description": " | ".join(ZONE_OPTIONS)},
        ]
        
        # Add mappings for Order and Sub-zones
        for zone, sub_zones in SOUS_ZONE_OPTIONS_BY_ZONE.items():
            if sub_zones:
                guide_data.append({"Règle": f"Sous-zones pour: {zone}", "Description": " | ".join(sub_zones)})
                
        for zone, sub_zones in ORDRE_TEMPLATES.items():
            for sub, templates in sub_zones.items():
                items = [f"{t['ordre']}={t['nom']}" for t in templates]
                guide_data.append({"Règle": f"Ordres pour: {sub}", "Description": " | ".join(items)})
                
        df_guide = pd.DataFrame(guide_data)

        # Create an Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Machines')
            df_guide.to_excel(writer, index=False, sheet_name='Guide des Règles')
            
            # Adjust column widths for better readability
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
        # Read the file into a pandas DataFrame
        contents = await file.read()
        
        if file.filename.endswith('.csv'):
            try:
                df = pd.read_csv(io.BytesIO(contents), sep=None, engine='python')
            except Exception:
                # Fallback to standard comma if autodetect fails
                df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
            
        # Clean up dataframe (strip whitespace from column names and string values, replace NaNs)
        df.columns = df.columns.str.strip().str.lower()
        if hasattr(df, 'map'):
            df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        else:
            df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
        df = df.where(pd.notnull(df), None)
        
        # Check if basic columns exist
        if 'zone' not in df.columns or 'sous_zone' not in df.columns or 'ordre' not in df.columns:
            # Maybe the user kept the long name for 'nom'
            pass
            
        # Prepare validation
        results = []
        
        # Get existing machine names to check for duplicates
        stmt = select(Machines.nom)
        db_result = await db.execute(stmt)
        existing_names = set([row[0] for row in db_result.all()])
        
        file_names_seen = set()
        
        for index, row_data in df.iterrows():
            row_dict = row_data.to_dict()
            
            # Retrieve values safely
            raw_nom = None
            for key in row_dict.keys():
                if 'nom' in key.lower():
                    raw_nom = str(row_dict[key]).strip() if pd.notnull(row_dict[key]) and str(row_dict[key]).strip() else None
                    break
                    
            r_zone = str(row_dict.get('zone', '')).strip() if pd.notnull(row_dict.get('zone')) else ''
            r_sous_zone = str(row_dict.get('sous_zone', '')).strip() if pd.notnull(row_dict.get('sous_zone')) else ''
            
            # Clean up 'ordre' (could be 1.0 from pandas float parsing)
            r_ordre = str(row_dict.get('ordre', '')).replace('.0', '').strip() if pd.notnull(row_dict.get('ordre')) else ''
            r_statut = str(row_dict.get('statut', '')).strip() if pd.notnull(row_dict.get('statut')) else ''
            if not r_statut:
                r_statut = 'OPERATIONNELLE'
                
            errors = []
            warnings = []
            valid = True
            
            # 1. Structural Validations
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
                        
                # Validate order
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
            
            # 2. Name generation or validation
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
                
            # 3. Duplicate checks
            if final_name and valid:
                if final_name in existing_names:
                    errors.append(f"La machine '{final_name}' existe déjà en base de données.")
                    valid = False
                if final_name in file_names_seen:
                    errors.append(f"Le nom '{final_name}' apparaît plusieurs fois dans ce fichier (vérifiez vos zones et ordres).")
                    valid = False
                else:
                    file_names_seen.add(final_name)
            
            # Reconstruct the row with valid keys for the frontend
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
                "row_index": index + 2, # +2 because 0-based and 1 header row
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