from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func


class Ordres_travail(Base):
    __tablename__ = "ordres_travail"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    titre = Column(String(255), nullable=False)  # US-CHETOP-001: Title of work order
    description = Column(Text, nullable=False)  # US-CHETOP-001: Detailed description
    priorite = Column(String(20), nullable=False, default="MOYENNE")  # US-CHETOP-002: BASSE, MOYENNE, ÉLEVÉE, URGENTE
    machine_id = Column(Integer, nullable=False)  # US-CHETOP-003: Associated machine
    utilisateur_id = Column(Integer, nullable=True)  # US-CHETOP-005: Assigned user
    date_echeance = Column(DateTime(timezone=True), nullable=True)  # US-CHETOP-001: Due date
    statut = Column(String(20), nullable=False, default="EN_ATTENTE")  # US-CHETOP-004: EN_ATTENTE, EN_COURS, TERMINÉ, ANNULÉ
    created_by = Column(Integer, nullable=True)
    validated_by = Column(Integer, nullable=True)
    date_validation = Column(DateTime(timezone=True), nullable=True)
    estimated_duration = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)