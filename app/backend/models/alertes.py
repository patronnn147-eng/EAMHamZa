from core.database import Base
from sqlalchemy import Column, DateTime, Enum, Integer, String, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum


class AlertType(str, enum.Enum):
    RUL_WARNING = "RUL_WARNING"
    FAILURE_PREDICTED = "FAILURE_PREDICTED"
    ANOMALY_DETECTED = "ANOMALY_DETECTED"
    PARTS_SHORTAGE = "PARTS_SHORTAGE"


class AlertSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Alert(Base):
    __tablename__ = "alertes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    alert_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False)
    alert_type = Column(Enum(AlertType), nullable=False)
    severity = Column(Enum(AlertSeverity), nullable=False)
    message = Column(Text, nullable=False)
    rul_days = Column(Float, nullable=True)
    failure_probability = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_linked_to_wo = Column(Boolean, default=False, nullable=False)
    work_order_id = Column(Integer, ForeignKey("ordres_travail.id", ondelete="SET NULL"), nullable=True)
    priority = Column(String(20), nullable=True, default="MEDIUM")  # LOW, MEDIUM, HIGH, URGENT
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    dismissed_at = Column(DateTime(timezone=True), nullable=True)
    dismissed_by = Column(Integer, ForeignKey("utilisateurs.id"), nullable=True)

    # Relationships
    machine = relationship("Machines", back_populates="alerts")
    user = relationship("Utilisateurs", back_populates="dismissed_alerts")
    work_order = relationship("Ordres_travail", back_populates="linked_alerts")


class AlertConfig(Base):
    __tablename__ = "alertes_config"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    rul_threshold_days = Column(Float, nullable=False, default=7.0)
    failure_probability_threshold = Column(Float, nullable=False, default=0.7)
    enable_rul_alerts = Column(Boolean, default=True, nullable=False)
    enable_failure_alerts = Column(Boolean, default=True, nullable=False)
    enable_anomaly_alerts = Column(Boolean, default=True, nullable=False)
    notification_in_app = Column(Boolean, default=True, nullable=False)
    notification_email = Column(Boolean, default=False, nullable=False)
    frequency = Column(String(20), nullable=False, default="real-time")  # real-time, daily, weekly
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)