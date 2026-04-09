from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String, Boolean


class Notifications(Base):
    __tablename__ = "notifications"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    utilisateur_id = Column(Integer, nullable=False)
    titre = Column(String, nullable=False)  # Title of the notification
    priorite = Column(String, nullable=True)  # Priority of the notification
    type = Column(String, nullable=False)  # PLANNING_ASSIGNMENT, STATUS_CHANGE, etc.
    message = Column(String, nullable=False)
    date_envoi = Column(DateTime(timezone=True), nullable=True)
    lu = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=True)