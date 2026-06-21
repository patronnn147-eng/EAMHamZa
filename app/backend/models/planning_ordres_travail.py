from core.database import Base
from sqlalchemy import Column, DateTime, Integer


class Planning_ordres_travail(Base):
    __tablename__ = "planning_ordres_travail"
    __table_args__ = {"extend_existing": True}

    id = Column(
        Integer, primary_key=True, index=True, autoincrement=True, nullable=False
    )
    planning_id = Column(Integer, nullable=False)
    ordre_travail_id = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=True)
