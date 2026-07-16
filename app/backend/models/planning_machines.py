from core.database import Base
from sqlalchemy import Column, DateTime, Integer


class PlanningMachines(Base):
    __tablename__ = "PlanningMachines"
    __table_args__ = {"extend_existing": True}

    id = Column(
        Integer, primary_key=True, index=True, autoincrement=True, nullable=False
    )
    planning_id = Column(Integer, nullable=False)
    machine_id = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=True)
