from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class Planning_ordres_travailData(BaseModel):
    """Entity data schema (for create/update)"""

    planning_id: int
    ordre_travail_id: Optional[int] = None
    created_at: Optional[datetime] = None


class Planning_ordres_travailUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""

    planning_id: Optional[int] = None
    ordre_travail_id: Optional[int] = None
    created_at: Optional[datetime] = None


class Planning_ordres_travailResponse(BaseModel):
    """Entity response schema"""

    id: int
    planning_id: int
    ordre_travail_id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Planning_ordres_travailListResponse(BaseModel):
    """List response schema"""

    items: List[Planning_ordres_travailResponse]
    total: int
    skip: int
    limit: int


class Planning_ordres_travailBatchCreateRequest(BaseModel):
    """Batch create request"""

    items: List[Planning_ordres_travailData]


class Planning_ordres_travailBatchUpdateItem(BaseModel):
    """Batch update item"""

    id: int
    updates: Planning_ordres_travailUpdateData


class Planning_ordres_travailBatchUpdateRequest(BaseModel):
    """Batch update request"""

    items: List[Planning_ordres_travailBatchUpdateItem]


class Planning_ordres_travailBatchDeleteRequest(BaseModel):
    """Batch delete request"""

    ids: List[int]
