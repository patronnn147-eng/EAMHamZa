from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_, select, func
from sqlalchemy.orm import Session

from core.database import get_db
from models.ordres_intervention import Interventions
from models.machines import Machines
from models.ordres_travail import Ordres_travail
from models.utilisateurs import Utilisateurs
from routers.auth import get_current_user

router = APIRouter()

# Pydantic schemas
class InterventionResponse(BaseModel):
    id: int
    titre: str
    description: str
    statut: str
    priorite: str
    machine_id: int
    machine_nom: Optional[str] = None
    technicien_id: Optional[int] = None
    technicien_nom: Optional[str] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class WorkOrderResponse(BaseModel):
    id: int
    titre: str
    description: str
    statut: str
    priorite: str
    machine_id: int
    machine_nom: Optional[str] = None
    utilisateur_id: Optional[int] = None
    utilisateur_nom: Optional[str] = None
    date_echeance: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class MachineResponse(BaseModel):
    id: int
    identifiant_machine: str
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
    created_at: datetime

    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_interventions: int
    interventions_en_cours: int
    interventions_termines: int
    interventions_urgents: int
    total_ordres_travail: int
    ordres_en_attente: int
    ordres_en_cours: int
    total_techniciens: int
    techniciens_disponibles: int
    total_machines: int
    machines_critiques: int

# Helper function to check if user has CHEFTECH role
async def verify_cheftech(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "CHEFTECH":
        raise HTTPException(status_code=403, detail="Accès non autorisé. Rôle CHEFTECH requis.")
    return current_user

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: dict = Depends(verify_cheftech),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics for CHEFTECH (US-CHEFTECH-001)"""
    try:
        # Intervention statistics
        total_interventions = db.scalar(select(func.count(Interventions.id)))
        interventions_en_cours = db.scalar(
            select(func.count(Interventions.id)).where(Interventions.statut == "EN_COURS")
        )
        interventions_termines = db.scalar(
            select(func.count(Interventions.id)).where(Interventions.statut == "TERMINÉ")
        )
        interventions_urgents = db.scalar(
            select(func.count(Interventions.id)).where(Interventions.priorite == "URGENTE")
        )

        # Work order statistics
        total_ordres_travail = db.scalar(select(func.count(Ordres_travail.id)))
        ordres_en_attente = db.scalar(
            select(func.count(Ordres_travail.id)).where(Ordres_travail.statut == "EN_ATTENTE")
        )
        ordres_en_cours = db.scalar(
            select(func.count(Ordres_travail.id)).where(Ordres_travail.statut == "EN_COURS")
        )

        # Technician statistics
        total_techniciens = db.scalar(
            select(func.count(Utilisateurs.id)).where(Utilisateurs.role == "TECHNICIEN")
        )
        # Technicians available (not currently assigned to active interventions)
        techniciens_disponibles = db.scalar(
            select(func.count(Utilisateurs.id))
            .where(
                and_(
                    Utilisateurs.role == "TECHNICIEN",
                    ~Utilisateurs.id.in_(
                        select(Interventions.technicien_id).where(Interventions.statut == "EN_COURS")
                    )
                )
            )
        )

        # Machine statistics
        total_machines = db.scalar(select(func.count(Machines.id)))
        machines_critiques = db.scalar(
            select(func.count(Machines.id)).where(Machines.statut == "CRITIQUE")
        )

        return DashboardStats(
            total_interventions=total_interventions or 0,
            interventions_en_cours=interventions_en_cours or 0,
            interventions_termines=interventions_termines or 0,
            interventions_urgents=interventions_urgents or 0,
            total_ordres_travail=total_ordres_travail or 0,
            ordres_en_attente=ordres_en_attente or 0,
            ordres_en_cours=ordres_en_cours or 0,
            total_techniciens=total_techniciens or 0,
            techniciens_disponibles=techniciens_disponibles or 0,
            total_machines=total_machines or 0,
            machines_critiques=machines_critiques or 0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/interventions", response_model=List[InterventionResponse])
async def get_interventions(
    statut: Optional[str] = Query(None, description="Filter by status"),
    priorite: Optional[str] = Query(None, description="Filter by priority"),
    technicien_id: Optional[int] = Query(None, description="Filter by technician"),
    current_user: dict = Depends(verify_cheftech),
    db: Session = Depends(get_db)
):
    """Get interventions with filters (US-CHEFTECH-002)"""
    try:
        query = (
            select(
                Interventions,
                Machines.nom.label("machine_nom"),
                Utilisateurs.nom.label("technicien_nom")
            )
            .outerjoin(Machines, Interventions.machine_id == Machines.id)
            .outerjoin(Utilisateurs, Interventions.technicien_id == Utilisateurs.id)
        )

        # Apply filters
        if statut:
            query = query.where(Interventions.statut == statut)
        if priorite:
            query = query.where(Interventions.priorite == priorite)
        if technicien_id:
            query = query.where(Interventions.technicien_id == technicien_id)

        query = query.order_by(Interventions.created_at.desc())
        result = db.execute(query)

        interventions = []
        for row in result:
            intervention, machine_nom, technicien_nom = row
            interventions.append(InterventionResponse(
                id=intervention.id,
                titre=intervention.titre,
                description=intervention.description,
                statut=intervention.statut,
                priorite=intervention.priorite,
                machine_id=intervention.machine_id,
                machine_nom=machine_nom,
                technicien_id=intervention.technicien_id,
                technicien_nom=technicien_nom,
                date_debut=intervention.date_debut,
                date_fin=intervention.date_fin,
                created_at=intervention.created_at,
                updated_at=intervention.updated_at
            ))

        return interventions
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/ordres-travail", response_model=List[WorkOrderResponse])
async def get_work_orders(
    statut: Optional[str] = Query(None, description="Filter by status"),
    priorite: Optional[str] = Query(None, description="Filter by priority"),
    current_user: dict = Depends(verify_cheftech),
    db: Session = Depends(get_db)
):
    """Get work orders with filters (US-CHEFTECH-003)"""
    try:
        query = (
            select(
                Ordres_travail,
                Machines.nom.label("machine_nom"),
                Utilisateurs.nom.label("utilisateur_nom")
            )
            .outerjoin(Machines, Ordres_travail.machine_id == Machines.id)
            .outerjoin(Utilisateurs, Ordres_travail.utilisateur_id == Utilisateurs.id)
        )

        # Apply filters
        if statut:
            query = query.where(Ordres_travail.statut == statut)
        if priorite:
            query = query.where(Ordres_travail.priorite == priorite)

        query = query.order_by(Ordres_travail.created_at.desc())
        result = db.execute(query)

        work_orders = []
        for row in result:
            ordre, machine_nom, utilisateur_nom = row
            work_orders.append(WorkOrderResponse(
                id=ordre.id,
                titre=ordre.titre,
                description=ordre.description,
                statut=ordre.statut,
                priorite=ordre.priorite,
                machine_id=ordre.machine_id,
                machine_nom=machine_nom,
                utilisateur_id=ordre.utilisateur_id,
                utilisateur_nom=utilisateur_nom,
                date_echeance=ordre.date_echeance,
                created_at=ordre.created_at,
                updated_at=ordre.updated_at
            ))

        return work_orders
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/techniciens", response_model=List[TechnicianResponse])
async def get_technicians(
    disponible: Optional[bool] = Query(None, description="Filter by availability"),
    current_user: dict = Depends(verify_cheftech),
    db: Session = Depends(get_db)
):
    """Get technicians list (US-CHEFTECH-004)"""
    try:
        query = select(Utilisateurs).where(Utilisateurs.role == "TECHNICIEN")

        if disponible:
            # Get technicians not assigned to active interventions
            active_technician_ids = (
                select(Interventions.technicien_id)
                .where(Interventions.statut == "EN_COURS")
                .where(Interventions.technicien_id.isnot(None))
            )
            query = query.where(~Utilisateurs.id.in_(active_technician_ids))

        result = db.execute(query)
        technicians = [
            TechnicianResponse(
                id=tech.id,
                nom=tech.nom,
                email=tech.email,
                role=tech.role,
                created_at=tech.created_at
            )
            for tech in result.scalars()
        ]

        return technicians
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/machines", response_model=List[MachineResponse])
async def get_machines(
    statut: Optional[str] = Query(None, description="Filter by status"),
    maintenance_required: Optional[bool] = Query(None, description="Filter by maintenance requirement"),
    current_user: dict = Depends(verify_cheftech),
    db: Session = Depends(get_db)
):
    """Get machines with technical status (US-CHEFTECH-005)"""
    try:
        query = select(Machines)

        # Apply filters
        if statut:
            query = query.where(Machines.statut == statut)
        
        if maintenance_required:
            # Machines requiring maintenance (past next maintenance date or critical status)
            query = query.where(
                or_(
                    Machines.statut == "CRITIQUE",
                    and_(
                        Machines.date_prochaine_maintenance.isnot(None),
                        Machines.date_prochaine_maintenance <= datetime.now()
                    )
                )
            )

        query = query.order_by(Machines.nom)
        result = db.execute(query)

        machines = [
            MachineResponse(
                id=machine.id,
                identifiant_machine=machine.identifiant_machine,
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
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/interventions/{intervention_id}/assign")
async def assign_technician(
    intervention_id: int,
    technicien_id: int,
    current_user: dict = Depends(verify_cheftech),
    db: Session = Depends(get_db)
):
    """Assign technician to intervention (US-CHEFTECH-006)"""
    try:
        # Check if intervention exists
        intervention = db.scalar(
            select(Interventions).where(Interventions.id == intervention_id)
        )
        if not intervention:
            raise HTTPException(status_code=404, detail="Intervention non trouvée")

        # Check if technician exists and is available
        technician = db.scalar(
            select(Utilisateurs).where(
                and_(
                    Utilisateurs.id == technicien_id,
                    Utilisateurs.role == "TECHNICIEN"
                )
            )
        )
        if not technician:
            raise HTTPException(status_code=404, detail="Technicien non trouvé")

        # Update intervention
        intervention.technicien_id = technicien_id
        intervention.updated_at = datetime.now()
        
        # If status is EN_ATTENTE, change to EN_COURS
        if intervention.statut == "EN_ATTENTE":
            intervention.statut = "EN_COURS"
            intervention.date_debut = datetime.now()

        db.commit()
        return {"message": "Technicien assigné avec succès"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/machines/{machine_id}/status")
async def update_machine_status(
    machine_id: int,
    statut: str,
    current_user: dict = Depends(verify_cheftech),
    db: Session = Depends(get_db)
):
    """Update machine status (US-CHEFTECH-007)"""
    try:
        machine = db.scalar(select(Machines).where(Machines.id == machine_id))
        if not machine:
            raise HTTPException(status_code=404, detail="Machine non trouvée")

        valid_statuses = ["ACTIF", "INACTIF", "MAINTENANCE", "CRITIQUE", "HORS_SERVICE"]
        if statut not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Statut invalide. Valeurs valides: {valid_statuses}")

        machine.statut = statut
        db.commit()
        return {"message": "Statut de la machine mis à jour avec succès"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

# Export router
router
