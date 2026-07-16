from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class OrdresInterventionData(BaseModel):
    """Entity data schema (for create/update)"""

    date_intervention: datetime
    rapport: Optional[str] = None
    ordre_travail_id: Optional[int] = None
    technicien_id: Optional[int] = None
    statut: Optional[str] = None
    problem_description: Optional[str] = None
    priority: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
    required_materials: Optional[str] = None
    machine_id: Optional[int] = None
    requested_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    created_at: Optional[datetime] = None
    actual_failure_type: Optional[str] = None
    ml_prediction_matched: Optional[bool] = None


class OrdresInterventionUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""

    date_intervention: Optional[datetime] = None
    rapport: Optional[str] = None
    ordre_travail_id: Optional[int] = None
    technicien_id: Optional[int] = None
    statut: Optional[str] = None
    problem_description: Optional[str] = None
    priority: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
    required_materials: Optional[str] = None
    machine_id: Optional[int] = None
    requested_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    created_at: Optional[datetime] = None
    actual_failure_type: Optional[str] = None
    ml_prediction_matched: Optional[bool] = None


class OrdresInterventionResponse(BaseModel):
    """Entity response schema"""

    id: int
    date_intervention: datetime
    rapport: Optional[str] = None
    ordre_travail_id: Optional[int] = None
    technicien_id: Optional[int] = None
    statut: Optional[str] = None
    problem_description: Optional[str] = None
    priority: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
    required_materials: Optional[str] = None
    machine_id: Optional[int] = None
    requested_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    created_at: Optional[datetime] = None
    actual_failure_type: Optional[str] = None
    ml_prediction_matched: Optional[bool] = None

    class Config:
        from_attributes = True


class OrdresInterventionValidationData(BaseModel):
    action: str  # "APPROVE" or "REJECT"
    technicien_id: Optional[int] = None  # Technician to assign
    rejection_reason: Optional[str] = None


class OrdresInterventionListResponse(BaseModel):
    """List response schema"""

    items: List[OrdresInterventionResponse]
    total: int
    skip: int
    limit: int


class OrdresInterventionBatchCreateRequest(BaseModel):
    """Batch create request"""

    items: List[OrdresInterventionData]


class OrdresInterventionBatchUpdateItem(BaseModel):
    """Batch update item"""

    id: int
    updates: OrdresInterventionUpdateData


class OrdresInterventionBatchUpdateRequest(BaseModel):
    """Batch update request"""

    items: List[OrdresInterventionBatchUpdateItem]


class OrdresInterventionBatchDeleteRequest(BaseModel):
    """Batch delete request"""

    ids: List[int]
