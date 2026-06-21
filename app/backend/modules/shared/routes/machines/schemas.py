from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class MachinesData(BaseModel):
    """Entity data schema (for create/update)"""

    nom: str
    zone: Optional[str] = None
    sous_zone: Optional[str] = None
    ordre: Optional[str] = None
    statut: Optional[str] = None
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
    statut: Optional[str] = None
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
    statut: Optional[str] = None
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
