"""Pydantic schemas for inventory stock, reservations, and consumption."""
from decimal import Decimal
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, validator


# ── Existing schemas (kept for backwards compat) ─────────────────────────────

class StockResponse(BaseModel):
    id: int
    piece_id: int
    quantity: Decimal
    piece_name: Optional[str] = None
    piece_reference: Optional[str] = None
    min_stock: Optional[int] = None
    # NEW — computed available stock = quantity - sum(active reservations)
    available_quantity: Optional[Decimal] = None

    class Config:
        from_attributes = True


class StockAddRequest(BaseModel):
    piece_id: int = Field(..., description="ID of the spare part")
    quantity: Decimal = Field(..., gt=0, description="Quantity to add")
    unit: Optional[str] = Field(None, description="Optional unit override (defaults to piece.default_unit)")
    reference: Optional[str] = Field(None, max_length=200, description="Optional reference (purchase order…)")


class StockConsumeRequest(BaseModel):
    piece_id: int = Field(..., description="ID of the spare part")
    quantity: Decimal = Field(..., gt=0, description="Quantity to consume")
    unit: Optional[str] = None
    intervention_id: Optional[int] = Field(None, description="Related intervention ID")
    reference: Optional[str] = Field(None, max_length=200)


class MouvementStockResponse(BaseModel):
    id: int
    piece_id: Optional[int] = None
    pending_piece_id: Optional[int] = None
    quantity: Decimal
    unit: str = "pcs"
    movement_type: str
    reference: Optional[str] = None
    intervention_id: Optional[int] = None
    created_at: Optional[datetime] = None
    piece_name: Optional[str] = None

    class Config:
        from_attributes = True


class AlerteStockResponse(BaseModel):
    piece_id: int
    piece_name: str
    piece_reference: str
    current_quantity: Decimal
    min_stock: int
    deficit: Decimal


# ── New: required / consumed / pending / reservation schemas ─────────────────

DISPOSITION_VALUES = ("used", "partial", "not_used", "wasted", "returned")
MOVEMENT_TYPE_VALUES = (
    "in",
    "out",
    "PENDING_OUT",
    "RESERVED",
    "RESERVATION_RELEASED",
    "REJECTED",
)
PENDING_STATUS_VALUES = ("PENDING_REVIEW", "MATCHED", "CREATED", "REJECTED")


class RequiredPieceItem(BaseModel):
    """One catalog piece planned for an intervention."""
    piece_id: int = Field(..., gt=0)
    quantity_planned: Decimal = Field(..., gt=0, le=Decimal("99999999.99"))
    unit: Optional[str] = Field(None, max_length=20)


class PendingPieceItem(BaseModel):
    """One uncatalogued piece submitted by a technician."""
    name: str = Field(..., min_length=1, max_length=200)
    quantity: Decimal = Field(..., gt=0, le=Decimal("99999999.99"))
    unit: str = Field("pcs", max_length=20)
    category: Optional[str] = Field(None, max_length=50)
    photo_object_key: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = Field(None, max_length=2000)


class ConsumedPieceItem(BaseModel):
    """Actual consumption at WO completion.

    `required_piece_id` links back to the reservation. Both quantities and
    disposition are validated:
      - all qty fields ≥ 0
      - sum(used + returned + wasted) ≤ planned (enforced server-side by DB trigger)
      - disposition value valid
    """
    required_piece_id: int = Field(..., gt=0)
    quantity_used: Decimal = Field(Decimal(0), ge=0)
    quantity_returned: Decimal = Field(Decimal(0), ge=0)
    quantity_wasted: Decimal = Field(Decimal(0), ge=0)
    disposition: str = Field(..., max_length=20)
    notes: Optional[str] = Field(None, max_length=2000)

    @validator("disposition")
    def _validate_disposition(cls, v: str) -> str:
        if v not in DISPOSITION_VALUES:
            raise ValueError(f"disposition must be one of {DISPOSITION_VALUES}")
        return v

    @validator("quantity_used", "quantity_returned", "quantity_wasted")
    def _validate_qty_precision(cls, v: Decimal) -> Decimal:
        # Cap at 2 decimal places — matches DB Numeric(10,2)
        return v.quantize(Decimal("0.01"))


# ── Responses ────────────────────────────────────────────────────────────────

class RequiredPieceResponse(BaseModel):
    id: int
    intervention_id: int
    piece_id: int
    piece_name: Optional[str] = None
    piece_reference: Optional[str] = None
    quantity_planned: Decimal
    unit: str
    quantity_reserved: Decimal
    reservation_expires_at: Optional[datetime] = None
    approved: Optional[bool] = None
    created_at: datetime
    # availability snapshot (computed at response time)
    available_quantity: Optional[Decimal] = None

    class Config:
        from_attributes = True


class ConsumedPieceResponse(BaseModel):
    id: int
    intervention_id: int
    required_piece_id: int
    piece_id: int
    piece_name: Optional[str] = None
    quantity_used: Decimal
    quantity_returned: Decimal
    quantity_wasted: Decimal
    unit: str
    disposition: str
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PendingPieceResponse(BaseModel):
    id: int
    intervention_id: Optional[int] = None
    submitted_by: Optional[int] = None
    submitted_by_name: Optional[str] = None
    name: str
    category: Optional[str] = None
    quantity: Decimal
    unit: str
    photo_object_key: Optional[str] = None
    notes: Optional[str] = None
    status: str
    matched_piece_id: Optional[int] = None
    matched_piece_name: Optional[str] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PendingPieceMatchRequest(BaseModel):
    matched_piece_id: int = Field(..., gt=0)


class PendingPieceRejectRequest(BaseModel):
    rejection_reason: str = Field(..., min_length=3, max_length=500)


class PieceSuggestion(BaseModel):
    """A fuzzy-match suggestion returned by /pieces/suggest."""
    piece_id: int
    name: str
    reference: str
    category: Optional[str] = None
    similarity: float = Field(..., ge=0.0, le=1.0)
    tier: str  # "high" (>=0.80) | "medium" (>=0.60) | "low" (>=0.40, hidden by default)
    machine_match: bool = False  # +0.1 boost flag


class AvailabilityResponse(BaseModel):
    piece_id: int
    stock_quantity: Decimal
    reserved_quantity: Decimal
    available_quantity: Decimal


# ── Reservation deficit reporting ────────────────────────────────────────────

class DeficitItem(BaseModel):
    piece_id: int
    piece_name: str
    requested: Decimal
    available: Decimal
    deficit: Decimal


class ReservationDeficitError(BaseModel):
    detail: str = "Stock insuffisant"
    missing: List[DeficitItem]

class ConsumedPieceDirect(BaseModel):
    """Ad-hoc consumption at WO completion time (no prior reservation).

    Used when technician realizes he needs a part during the intervention
    that wasn't planned. Handler creates a required_piece (approved=True,
    reserved=0) and a consumed_pieces row atomically.
    """
    piece_id: int = Field(..., gt=0)
    quantity: Decimal = Field(..., gt=0, le=Decimal("99999999.99"))
    unit: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = Field(None, max_length=2000)

    @validator("quantity")
    def _q(cls, v: Decimal) -> Decimal:
        return v.quantize(Decimal("0.01"))


class PendingPieceDirect(BaseModel):
    """Ad-hoc uncatalogued piece request at WO completion time."""
    name: str = Field(..., min_length=1, max_length=200)
    quantity: Decimal = Field(..., gt=0, le=Decimal("99999999.99"))
    unit: str = Field("pcs", max_length=20)
    category: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = Field(None, max_length=2000)

