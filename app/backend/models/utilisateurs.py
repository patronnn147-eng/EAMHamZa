from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String


class Utilisateurs(Base):
    __tablename__ = "utilisateurs"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    identifiant = Column(String, nullable=False)
    nom_utilisateur = Column(String, nullable=False)
    mot_de_passe_chiffre = Column(String, nullable=False)
    courriel = Column(String, nullable=False)
    role = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=True)