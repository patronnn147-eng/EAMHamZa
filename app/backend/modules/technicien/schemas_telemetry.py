from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class MachineTelemetryBase(BaseModel):
    """Base telemetry fields shared across request/response"""
    temperature: float = Field(..., description="Temperature in Celsius", ge=-50, le=200)
    vibration: float = Field(..., description="Vibration in mm/s", ge=0, le=100)
    rpm: int = Field(..., description="Rotational speed in RPM", ge=0, le=10000)
    torque: float = Field(..., description="Torque in Nm", ge=0, le=1000)
    power: float = Field(..., description="Power in kW", ge=0, le=500)
    notes: Optional[str] = None


class MachineTelemetryCreate(MachineTelemetryBase):
    """Schema for creating telemetry entry via work order completion"""
    machine_id: int
    work_order_id: Optional[int] = None
    recorded_at: datetime = Field(default_factory=datetime.utcnow)


class MachineTelemetryResponse(MachineTelemetryBase):
    """Schema for telemetry response"""
    id: int
    machine_id: int
    work_order_id: Optional[int] = None
    technician_id: int
    recorded_at: datetime
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MachineTelemetryLatest(BaseModel):
    """Schema for latest telemetry per machine"""
    machine_id: int
    machine_nom: Optional[str] = None
    temperature: float
    vibration: float
    rpm: int
    torque: float
    power: float
    recorded_at: datetime
    recorded_by: Optional[str] = None
    work_order_id: Optional[int] = None


class MachineTelemetryListResponse(BaseModel):
    """Paginated list response for machine telemetry"""
    items: List[MachineTelemetryResponse]
    total: int
    page: int
    size: int