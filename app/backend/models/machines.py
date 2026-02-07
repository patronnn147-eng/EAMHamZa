from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String


class Machines(Base):
    __tablename__ = "machines"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    identifiant_machine = Column(String, nullable=False)
    nom = Column(String, nullable=False)
    emplacement = Column(String, nullable=False)
    zone = Column(String, nullable=True)
    sous_zone = Column(String, nullable=True)
    statut = Column(String, nullable=False)
    type = Column(String, nullable=False)
    date_derniere_maintenance = Column(DateTime(timezone=True), nullable=True)
    date_prochaine_maintenance = Column(DateTime(timezone=True), nullable=True)
    image_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)