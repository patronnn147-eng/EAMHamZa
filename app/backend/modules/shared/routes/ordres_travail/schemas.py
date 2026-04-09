from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class Ordres_travailData(BaseModel):
    """Entity data schema (for create/update) - US-CHETOP-001"""
    titre: Optional[str] = None
    description: Optional[str] = None
    priorite: str = "MOYENNE"
    machine_id: int
    utilisateur_id: int = None
    date_echeance: Optional[datetime] = None
    statut: str = "EN_ATTENTE"
    created_at: Optional[datetime] = None


class Ordres_travailUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    titre: Optional[str] = None
    description: Optional[str] = None
    date_echeance: Optional[datetime] = None
    priorite: Optional[str] = None
    machine_id: Optional[int] = None
    utilisateur_id: Optional[int] = None
    ordre_id: Optional[int] = None
    statut: Optional[str] = None
    created_at: Optional[datetime] = None
    validated_by: Optional[int] = None
    date_validation: Optional[datetime] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    rapport: Optional[str] = None
    failure_type: Optional[str] = None


class Ordres_travailResponse(BaseModel):
    """Entity response schema"""
    id: int
    titre: str
    description: str
    priorite: str
    machine_id: int
    utilisateur_id: Optional[int] = None
    date_echeance: Optional[datetime] = None
    statut: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    validated_by: Optional[int] = None
    date_validation: Optional[datetime] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    rapport: Optional[str] = None
    failure_type: Optional[str] = None

    class Config:
        from_attributes = True


class Ordres_travailValidationData(BaseModel):
    action: str
    utilisateur_id: Optional[int] = None
    reason: Optional[str] = None


class Ordres_travailListResponse(BaseModel):
    """List response schema"""
    items: List[Ordres_travailResponse]
    total: int
    skip: int
    limit: int


class Ordres_travailBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Ordres_travailData]


class Ordres_travailBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Ordres_travailUpdateData


class Ordres_travailBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Ordres_travailBatchUpdateItem]


class Ordres_travailBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]
