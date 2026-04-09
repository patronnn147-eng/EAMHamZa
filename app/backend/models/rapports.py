from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String


class Rapports(Base):
    __tablename__ = "rapports"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    identifiant_rapport = Column(String, nullable=False)
    titre = Column(String, nullable=False)
    date_generation = Column(DateTime(timezone=True), nullable=False)
    contenu = Column(String, nullable=False)
    utilisateur_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)