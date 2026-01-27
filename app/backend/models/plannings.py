from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String


class Plannings(Base):
    __tablename__ = "plannings"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    identifiant_planning = Column(String, nullable=False)
    date_debut = Column(DateTime(timezone=True), nullable=False)
    date_fin = Column(DateTime(timezone=True), nullable=False)
    type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=True)