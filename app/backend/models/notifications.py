from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String, Boolean


class Notifications(Base):
    __tablename__ = "notifications"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    utilisateur_id = Column(Integer, nullable=False)
    titre = Column(String, nullable=False)
    message = Column(String, nullable=False)
    type = Column(String, nullable=False)  # ASSIGNMENT, STATUS_CHANGE, URGENT_ALERT, COMMENT
    priorite = Column(String, nullable=False)  # NORMALE, URGENTE
    lu = Column(Boolean, default=False, nullable=False)
    ordre_travail_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)