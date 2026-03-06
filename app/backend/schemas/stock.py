from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class StockResponse(BaseModel):
    id: int
    piece_id: int
    quantity: int
    piece_name: Optional[str] = None
    piece_reference: Optional[str] = None
    min_stock: Optional[int] = None

    class Config:
        from_attributes = True


class StockAddRequest(BaseModel):
    piece_id: int = Field(..., description="ID of the spare part")
    quantity: int = Field(..., gt=0, description="Quantity to add")
    reference: Optional[str] = Field(None, description="Optional reference (e.g., purchase order)")


class StockConsumeRequest(BaseModel):
    piece_id: int = Field(..., description="ID of the spare part")
    quantity: int = Field(..., gt=0, description="Quantity to consume")
    intervention_id: Optional[int] = Field(None, description="Related intervention ID")
    reference: Optional[str] = Field(None, description="Optional reference")


class MouvementStockResponse(BaseModel):
    id: int
    piece_id: int
    quantity: int
    movement_type: str
    reference: Optional[str] = None
    created_at: Optional[datetime] = None
    piece_name: Optional[str] = None

    class Config:
        from_attributes = True


class AlerteStockResponse(BaseModel):
    piece_id: int
    piece_name: str
    piece_reference: str
    current_quantity: int
    min_stock: int
    deficit: int
