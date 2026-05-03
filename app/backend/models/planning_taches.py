from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String, Text, Enum as SQLEnum
from sqlalchemy.sql import func
import enum


class TaskType(str, enum.Enum):
    """CHEFTECH execution-task type"""
    DIAGNOSTIC = "DIAGNOSTIC"
    CORRECTION = "CORRECTION"


class Planning_taches(Base):
    """Detailed execution tasks defined by CHEFTECH for a planning before submission."""
    __tablename__ = "planning_taches"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    planning_id = Column(Integer, nullable=False, index=True)
    titre = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    technicien_id = Column(Integer, nullable=False)
    machine_id = Column(Integer, nullable=False)
    task_type = Column(SQLEnum(TaskType), nullable=False)
    date_debut = Column(DateTime(timezone=True), nullable=False)
    date_fin = Column(DateTime(timezone=True), nullable=False)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
