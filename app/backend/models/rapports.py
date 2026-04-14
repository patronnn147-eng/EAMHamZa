from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String, Boolean, JSON
from sqlalchemy.sql import func
import enum


class ReportType(str, enum.Enum):
    WEEKLY_DIGEST = "WEEKLY_DIGEST"
    MONTHLY_SUMMARY = "MONTHLY_SUMMARY"
    ASSET_HEALTH = "ASSET_HEALTH"
    MAINTENANCE_COSTS = "MAINTENANCE_COSTS"
    ML_PREDICTIONS = "ML_PREDICTIONS"


class Rapports(Base):
    __tablename__ = "rapports"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    identifiant_rapport = Column(String, nullable=False)
    titre = Column(String, nullable=False)
    date_generation = Column(DateTime(timezone=True), nullable=False)
    contenu = Column(String, nullable=False)
    utilisateur_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)
    
    # Scheduling fields
    report_type = Column(String(50), nullable=True)
    schedule_config = Column(JSON, nullable=True)
    last_sent_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)