from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func


class Ordres_intervention(Base):
    __tablename__ = "ordres_intervention"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    date_intervention = Column(DateTime(timezone=True), nullable=False)
    rapport = Column(String, nullable=True)
    ordre_travail_id = Column(Integer, nullable=False)
    technicien_id = Column(Integer, nullable=True)
    statut = Column(String(20), nullable=False, default="EN_ATTENTE")
    problem_description = Column(Text, nullable=True)
    priority = Column(String(20), nullable=True)
    estimated_duration_minutes = Column(Integer, nullable=True)
    required_materials = Column(Text, nullable=True)
    machine_id = Column(Integer, nullable=True)
    requested_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(Integer, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    date_debut = Column(DateTime(timezone=True), nullable=True)
    date_fin = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)