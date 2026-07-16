from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String


class MaintenancesPlanifiees(Base):
    __tablename__ = "MaintenancesPlanifiees"
    __table_args__ = {"extend_existing": True}

    id = Column(
        Integer, primary_key=True, index=True, autoincrement=True, nullable=False
    )
    utilisateur_id = Column(Integer, nullable=True)
    rapport_id = Column(Integer, nullable=True)
    date_planifiee = Column(DateTime(timezone=True), nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)
