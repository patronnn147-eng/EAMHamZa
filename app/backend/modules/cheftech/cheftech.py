from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, or_, select, func, cast, String
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.ordres_intervention import Ordres_intervention
from models.machines import Machines
from models.ordres_travail import Ordres_travail
from models.utilisateurs import Utilisateurs, UserRole
from modules.auth.auth import get_current_user

router = APIRouter(prefix="/api/v1/cheftech", tags=["cheftech"])

# Pydantic schemas
class InterventionResponse(BaseModel):
    id: int
    date_intervention: datetime
    rapport: Optional[str] = None
    ordre_travail_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class WorkOrderResponse(BaseModel):
    id: int
    titre: str
    description: str
    statut: str
    priorite: str
    machine_id: int
    utilisateur_id: Optional[int] = None
    date_echeance: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class MachineResponse(BaseModel):
    id: int
    nom: str
    emplacement: str
    statut: str
    type: str
    date_derniere_maintenance: Optional[datetime] = None
    date_prochaine_maintenance: Optional[datetime] = None
    image_url: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TechnicianResponse(BaseModel):
    id: int
    nom: str
    email: str
    role: str

    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_interventions: int
    total_ordres_travail: int
    ordres_en_attente: int
    ordres_en_cours: int
    total_techniciens: int
    total_machines: int
    machines_critiques: int

class WorkOrderAssignRequest(BaseModel):
    technicien_ids: List[int]
    estimated_completion_date: Optional[datetime] = None

# Helper function to check if user has CHEFTECH role
async def verify_cheftech(current_user: Utilisateurs = Depends(get_current_user)):
    if current_user.role != "CHEFTECH":
        raise HTTPException(status_code=403, detail="Accès non autorisé. Rôle CHEFTECH requis.")
    return current_user

async def verify_cheftech_or_admin(current_user: Utilisateurs = Depends(get_current_user)):
    if current_user.role not in ["CHEFTECH", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Accès non autorisé. Rôle CHEFTECH ou ADMIN requis.")
    return current_user

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: Utilisateurs = Depends(verify_cheftech),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard statistics for CHEFTECH"""
    try:
        # Intervention statistics
        total_interventions = await db.scalar(select(func.count(Ordres_intervention.id)))

        # Work order statistics
        total_ordres_travail = await db.scalar(select(func.count(Ordres_travail.id)))
        ordres_en_attente = await db.scalar(
            select(func.count(Ordres_travail.id)).where(Ordres_travail.statut == "EN_ATTENTE")
        )
        ordres_en_cours = await db.scalar(
            select(func.count(Ordres_travail.id)).where(Ordres_travail.statut == "EN_COURS")
        )

        # Technician statistics
        total_techniciens = await db.scalar(
            select(func.count(Utilisateurs.id)).where(cast(Utilisateurs.role, String) == "TECHNICIEN")
        )

        # Machine statistics
        total_machines = await db.scalar(select(func.count(Machines.id)))
        machines_critiques = await db.scalar(
            select(func.count(Machines.id)).where(Machines.statut == "CRITIQUE")
        )

        return DashboardStats(
            total_interventions=total_interventions or 0,
            total_ordres_travail=total_ordres_travail or 0,
            ordres_en_attente=ordres_en_attente or 0,
            ordres_en_cours=ordres_en_cours or 0,
            total_techniciens=total_techniciens or 0,
            total_machines=total_machines or 0,
            machines_critiques=machines_critiques or 0
        )
    except Exception as e:
        print(f"Error in dashboard stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/interventions", response_model=List[InterventionResponse])
async def get_interventions(
    current_user: Utilisateurs = Depends(verify_cheftech),
    db: AsyncSession = Depends(get_db)
):
    """Get all interventions"""
    try:
        query = select(Ordres_intervention).order_by(Ordres_intervention.date_intervention.desc())
        result = await db.execute(query)

        interventions = [
            InterventionResponse(
                id=intervention.id,
                date_intervention=intervention.date_intervention,
                rapport=intervention.rapport,
                ordre_travail_id=intervention.ordre_travail_id,
                created_at=intervention.created_at
            )
            for intervention in result.scalars()
        ]

        return interventions
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/ordres-travail", response_model=List[WorkOrderResponse])
async def get_work_orders(
    statut: Optional[str] = Query(None, description="Filter by status"),
    current_user: Utilisateurs = Depends(verify_cheftech),
    db: AsyncSession = Depends(get_db)
):
    """Get work orders with optional status filter"""
    try:
        query = select(Ordres_travail)

        # Apply filter
        if statut:
            query = query.where(Ordres_travail.statut == statut)

        query = query.order_by(Ordres_travail.created_at.desc())
        result = await db.execute(query)

        work_orders = [
            WorkOrderResponse(
                id=ordre.id,
                titre=ordre.titre,
                description=ordre.description,
                statut=ordre.statut,
                priorite=ordre.priorite,
                machine_id=ordre.machine_id,
                utilisateur_id=ordre.utilisateur_id,
                date_echeance=ordre.date_echeance,
                created_at=ordre.created_at,
                updated_at=ordre.updated_at
            )
            for ordre in result.scalars()
        ]

        return work_orders
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/techniciens", response_model=List[TechnicianResponse])
async def get_technicians(
    current_user: Utilisateurs = Depends(verify_cheftech),
    db: AsyncSession = Depends(get_db)
):
    """Get all technicians"""
    try:
        query = select(Utilisateurs).where(cast(Utilisateurs.role, String) == "TECHNICIEN")
        query = query.order_by(Utilisateurs.nom)
        result = await db.execute(query)

        technicians = [
            TechnicianResponse(
                id=tech.id,
                nom=tech.nom,
                email=tech.email,
                role=tech.role
            )
            for tech in result.scalars()
        ]

        return technicians
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/machines", response_model=List[MachineResponse])
async def get_machines(
    statut: Optional[str] = Query(None, description="Filter by status"),
    current_user: Utilisateurs = Depends(verify_cheftech),
    db: AsyncSession = Depends(get_db)
):
    """Get machines with optional status filter"""
    try:
        query = select(Machines)

        # Apply filter
        if statut:
            query = query.where(Machines.statut == statut)

        query = query.order_by(Machines.nom)
        result = await db.execute(query)

        machines = [
            MachineResponse(
                id=machine.id,
                nom=machine.nom,
                emplacement=machine.emplacement,
                statut=machine.statut,
                type=machine.type,
                date_derniere_maintenance=machine.date_derniere_maintenance,
                date_prochaine_maintenance=machine.date_prochaine_maintenance,
                image_url=machine.image_url,
                created_at=machine.created_at
            )
            for machine in result.scalars()
        ]

        return machines
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/ordres-travail/{ordre_id}/assign")
async def assign_work_order(
    ordre_id: int,
    data: WorkOrderAssignRequest,
    current_user: Utilisateurs = Depends(verify_cheftech_or_admin),
    db: AsyncSession = Depends(get_db),
):
    if not data.technicien_ids:
        raise HTTPException(status_code=400, detail="technicien_ids is required")

    ordre = await db.scalar(select(Ordres_travail).where(Ordres_travail.id == ordre_id))
    if not ordre:
        raise HTTPException(status_code=404, detail="Work order not found")

    tech_result = await db.execute(
        select(Utilisateurs.id).where(
            and_(
                Utilisateurs.id.in_(data.technicien_ids),
                cast(Utilisateurs.role, String) == "TECHNICIEN",
            )
        )
    )
    found_ids = set(tech_result.scalars().all())
    missing = [tid for tid in data.technicien_ids if tid not in found_ids]
    if missing:
        raise HTTPException(status_code=400, detail=f"Invalid technician ids: {missing}")

    now = datetime.utcnow()
    for technicien_id in data.technicien_ids:
        existing = await db.scalar(
            select(Ordres_intervention).where(
                and_(
                    Ordres_intervention.ordre_travail_id == ordre_id,
                    Ordres_intervention.technicien_id == technicien_id,
                )
            )
        )
        if existing:
            continue
        db.add(
            Ordres_intervention(
                date_intervention=now,
                ordre_travail_id=ordre_id,
                technicien_id=technicien_id,
                statut="EN_ATTENTE",
            )
        )

    ordre.statut = "ASSIGNÉ"
    ordre.validated_by = current_user.id
    ordre.date_validation = ordre.date_validation or now
    if data.estimated_completion_date:
        ordre.date_echeance = data.estimated_completion_date

    await db.commit()
    return {"message": "Work order assigned", "ordre_id": ordre_id, "technicien_ids": data.technicien_ids}

@router.put("/machines/{machine_id}/status")
async def update_machine_status(
    machine_id: int,
    statut: str,
    current_user: Utilisateurs = Depends(verify_cheftech),
    db: AsyncSession = Depends(get_db)
):
    """Update machine status"""
    try:
        machine = await db.scalar(select(Machines).where(Machines.id == machine_id))
        if not machine:
            raise HTTPException(status_code=404, detail="Machine non trouvée")

        valid_statuses = ["ACTIF", "INACTIF", "MAINTENANCE", "CRITIQUE", "HORS_SERVICE"]
        if statut not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Statut invalide. Valeurs valides: {valid_statuses}")

        machine.statut = statut
        await db.commit()
        return {"message": "Statut de la machine mis à jour avec succès"}
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

# Export router
router
