from pydantic import BaseModel, Field
from typing import Optional

class PieceBase(BaseModel):
    reference: str = Field(..., description="Unique part reference code")
    name: str = Field(..., description="Part name")
    description: Optional[str] = None
    unit_price: Optional[float] = None
    category: Optional[str] = None
    min_stock: Optional[int] = 5

class PieceCreate(PieceBase):
    pass

class PieceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    unit_price: Optional[float] = None
    category: Optional[str] = None
    min_stock: Optional[int] = None

class PieceResponse(PieceBase):
    id: int

    class Config:
        orm_mode = True
