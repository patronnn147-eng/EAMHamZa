from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class PlanningOrdresTravailData(BaseModel):
    """Entity data schema (for create/update)"""

    planning_id: int
    ordre_travail_id: Optional[int] = None
    created_at: Optional[datetime] = None


class PlanningOrdresTravailUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""

    planning_id: Optional[int] = None
    ordre_travail_id: Optional[int] = None
    created_at: Optional[datetime] = None


class PlanningOrdresTravailResponse(BaseModel):
    """Entity response schema"""

    id: int
    planning_id: int
    ordre_travail_id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PlanningOrdresTravailListResponse(BaseModel):
    """List response schema"""

    items: List[PlanningOrdresTravailResponse]
    total: int
    skip: int
    limit: int


class PlanningOrdresTravailBatchCreateRequest(BaseModel):
    """Batch create request"""

    items: List[PlanningOrdresTravailData]


class PlanningOrdresTravailBatchUpdateItem(BaseModel):
    """Batch update item"""

    id: int
    updates: PlanningOrdresTravailUpdateData


class PlanningOrdresTravailBatchUpdateRequest(BaseModel):
    """Batch update request"""

    items: List[PlanningOrdresTravailBatchUpdateItem]


class PlanningOrdresTravailBatchDeleteRequest(BaseModel):
    """Batch delete request"""

    ids: List[int]
