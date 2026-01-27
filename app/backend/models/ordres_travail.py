from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String


class Ordres_travail(Base):
    __tablename__ = "ordres_travail"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    date_echeance = Column(DateTime(timezone=True), nullable=False)
    priorite = Column(String, nullable=False)
    machine_id = Column(Integer, nullable=False)
    utilisateur_id = Column(Integer, nullable=True)
    ordre_id = Column(Integer, nullable=True)
    statut = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=True)