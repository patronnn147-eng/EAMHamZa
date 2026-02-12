from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String
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
    date_debut = Column(DateTime(timezone=True), nullable=True)
    date_fin = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)