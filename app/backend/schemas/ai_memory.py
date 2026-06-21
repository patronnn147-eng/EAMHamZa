from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime
from uuid import UUID


class AIMemoryCreate(BaseModel):
    """Schema for creating AI memory - utilisateur_id set from auth"""

    utilisateur_id: Optional[int] = None  # Auto-set from current user
    memory_type: Literal["preference", "strategy", "failure"]
    memory_key: str
    memory_value: str
    success_count: int = 0
    failure_count: int = 0


class AIMemoryUpdate(BaseModel):
    """Schema for updating AI memory"""

    memory_value: Optional[str] = None
    success_count: Optional[int] = None
    failure_count: Optional[int] = None


class AIMemoryResponse(BaseModel):
    """Schema for AI memory response"""

    id: UUID
    utilisateur_id: int
    memory_type: str
    memory_key: str
    memory_value: str
    success_count: int
    failure_count: int
    last_used: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AIMemoryListResponse(BaseModel):
    """Schema for listing AI memories"""

    memories: list[AIMemoryResponse]
    total: int
