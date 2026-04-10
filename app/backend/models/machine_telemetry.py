from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class MachineTelemetry(Base):
    __tablename__ = "machine_telemetry_logs"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    machine_id = Column(Integer, nullable=False, index=True)
    work_order_id = Column(Integer, nullable=True, index=True)
    technician_id = Column(Integer, nullable=False)

    temperature = Column(Float(), nullable=False)
    vibration = Column(Float(), nullable=False)
    rpm = Column(Integer(), nullable=False)
    torque = Column(Float(), nullable=False)
    power = Column(Float(), nullable=False)

    recorded_at = Column(DateTime(timezone=True), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)