from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class Ordres_interventionData(BaseModel):
    """Entity data schema (for create/update)"""

    date_intervention: datetime
    rapport: str = None
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


class Ordres_interventionUpdateData(BaseModel):
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


class Ordres_interventionResponse(BaseModel):
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


class Ordres_interventionValidationData(BaseModel):
    action: str  # "APPROVE" or "REJECT"
    technicien_id: Optional[int] = None  # Technician to assign
    rejection_reason: Optional[str] = None


class Ordres_interventionListResponse(BaseModel):
    """List response schema"""

    items: List[Ordres_interventionResponse]
    total: int
    skip: int
    limit: int


class Ordres_interventionBatchCreateRequest(BaseModel):
    """Batch create request"""

    items: List[Ordres_interventionData]


class Ordres_interventionBatchUpdateItem(BaseModel):
    """Batch update item"""

    id: int
    updates: Ordres_interventionUpdateData


class Ordres_interventionBatchUpdateRequest(BaseModel):
    """Batch update request"""

    items: List[Ordres_interventionBatchUpdateItem]


class Ordres_interventionBatchDeleteRequest(BaseModel):
    """Batch delete request"""

    ids: List[int]
