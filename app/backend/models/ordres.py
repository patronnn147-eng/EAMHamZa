from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String


class Ordres(Base):
    __tablename__ = "ordres"
    __table_args__ = {"extend_existing": True}

    id = Column(
        Integer, primary_key=True, index=True, autoincrement=True, nullable=False
    )
    identifiant = Column(String, nullable=False)
    titre = Column(String, nullable=False)
    description = Column(String, nullable=True)
    date_creation = Column(DateTime(timezone=True), nullable=False)
    statut = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=True)
