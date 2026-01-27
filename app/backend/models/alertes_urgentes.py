from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String


class Alertes_urgentes(Base):
    __tablename__ = "alertes_urgentes"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    utilisateur_id = Column(Integer, nullable=False)
    categorie = Column(String, nullable=False)  # SECURITE, PANNE_CRITIQUE, QUALITE
    description = Column(String, nullable=False)
    machine_id = Column(Integer, nullable=True)
    photo_url = Column(String, nullable=True)
    statut = Column(String, nullable=False)  # EN_ATTENTE, TRAITE
    ordre_travail_genere_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)