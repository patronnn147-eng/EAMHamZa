from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class MachineTelemetryBase(BaseModel):
    air_temperature: float = Field(
        ..., description="Air temperature in Kelvin", ge=250, le=400
    )
    process_temperature: float = Field(
        ..., description="Process temperature in Kelvin", ge=250, le=450
    )
    rotational_speed: int = Field(
        ..., description="Rotational speed in RPM", ge=0, le=10000
    )
    torque: float = Field(..., description="Torque in Nm", ge=0, le=1000)
    tool_wear: float = Field(..., description="Tool wear in minutes", ge=0, le=500)
    notes: Optional[str] = None


class MachineTelemetryCreate(MachineTelemetryBase):
    machine_id: int
    work_order_id: Optional[int] = None
    recorded_at: datetime = Field(default_factory=datetime.utcnow)


class MachineTelemetryResponse(MachineTelemetryBase):
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
    machine_id: int
    machine_nom: Optional[str] = None
    air_temperature: float
    process_temperature: float
    rotational_speed: int
    torque: float
    tool_wear: float
    recorded_at: datetime
    recorded_by: Optional[str] = None
    work_order_id: Optional[int] = None


class MachineTelemetryListResponse(BaseModel):
    items: List[MachineTelemetryResponse]
    total: int
    page: int
    size: int
