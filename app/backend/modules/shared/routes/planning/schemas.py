from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class PlanningCreateData(BaseModel):
    """Schema for creating a planning"""
    identifiant_planning: str
    date_debut: datetime
    date_fin: datetime
    type: str
    shift_type: Optional[str] = None
    chef_operation_id: Optional[int] = None
    chef_technique_id: Optional[int] = None
    zone_travail: Optional[str] = None
    technicien_ids: List[int] = Field(default_factory=list, description="List of technician IDs")
    machine_ids: List[int] = Field(default_factory=list, description="List of machine IDs")


class PlanningUpdateData(BaseModel):
    """Schema for updating a planning"""
    identifiant_planning: Optional[str] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    type: Optional[str] = None
    shift_type: Optional[str] = None
    chef_operation_id: Optional[int] = None
    chef_technique_id: Optional[int] = None
    zone_travail: Optional[str] = None
    technicien_ids: Optional[List[int]] = None
    machine_ids: Optional[List[int]] = None


class PlanningResponse(BaseModel):
    """Schema for planning response"""
    id: int
    identifiant_planning: str
    date_debut: datetime
    date_fin: datetime
    type: str
    shift_type: Optional[str] = None
    chef_operation_id: Optional[int] = None
    chef_technique_id: Optional[int] = None
    zone_travail: Optional[str] = None
    created_at: Optional[datetime] = None
    assigned_users: List[dict] = Field(default_factory=list)
    machine_ids: List[int] = Field(default_factory=list)

    class Config:
        from_attributes = True


class UserOption(BaseModel):
    """User option for dropdowns"""
    id: int
    nom: str
    email: str
    role: str
    shift_type: Optional[str] = None


class PlanningMachineResponse(BaseModel):
    """Machine as returned when listing planning machines"""

    id: int
    nom: str
    type: Optional[str] = None
    emplacement: Optional[str] = None
    zone: Optional[str] = None
    sous_zone: Optional[str] = None
    ordre: Optional[str] = None
    statut: Optional[str] = None
    date_derniere_maintenance: Optional[datetime] = None
    date_prochaine_maintenance: Optional[datetime] = None
    image_url: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
