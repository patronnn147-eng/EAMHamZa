from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String


class Archives(Base):
    __tablename__ = "archives"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    identifiant_archive = Column(String, nullable=False)
    nom = Column(String, nullable=False)
    date_archivage = Column(DateTime(timezone=True), nullable=False)
    type = Column(String, nullable=False)
    object_key = Column(String, nullable=True)
    ordre_travail_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)