from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String


class Commentaires(Base):
    __tablename__ = "commentaires"
    __table_args__ = {"extend_existing": True}

    id = Column(
        Integer, primary_key=True, index=True, autoincrement=True, nullable=False
    )
    ordre_travail_id = Column(Integer, nullable=False)
    utilisateur_id = Column(Integer, nullable=False)
    contenu = Column(String, nullable=False)
    fichier_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)
