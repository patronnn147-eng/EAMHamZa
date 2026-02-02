from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String, Enum as SQLEnum
import enum


class PlanningType(str, enum.Enum):
    """Planning types"""
    MAINTENANCE = "MAINTENANCE"
    SHIFT = "SHIFT"


class ShiftType(str, enum.Enum):
    """Shift types for SHIFT planning"""
    MORNING = "MORNING"
    NIGHT = "NIGHT"


class Plannings(Base):
    __tablename__ = "plannings"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    identifiant_planning = Column(String, nullable=False)
    date_debut = Column(DateTime(timezone=True), nullable=False)
    date_fin = Column(DateTime(timezone=True), nullable=False)
    type = Column(SQLEnum(PlanningType), nullable=False)
    shift_type = Column(SQLEnum(ShiftType), nullable=True)  # Only for SHIFT type
    chef_operation_id = Column(Integer, nullable=True)  # CHETOP user
    chef_technique_id = Column(Integer, nullable=True)  # CHEFTECH user
    created_at = Column(DateTime(timezone=True), nullable=True)