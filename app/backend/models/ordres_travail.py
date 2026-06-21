from core.database import Base
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum


class OrdreStatut(str, enum.Enum):
    """Work Order status including full workflow"""

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    VALIDATED = "VALIDATED"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"
    ANNULÉ = "ANNULÉ"


class Ordres_travail(Base):
    __tablename__ = "ordres_travail"
    __table_args__ = {"extend_existing": True}

    id = Column(
        Integer, primary_key=True, index=True, autoincrement=True, nullable=False
    )
    titre = Column(String(255), nullable=False)  # US-CHETOP-001: Title of work order
    description = Column(Text, nullable=False)  # US-CHETOP-001: Detailed description
    priorite = Column(
        String(20), nullable=False, default="MOYENNE"
    )  # US-CHETOP-002: BASSE, MOYENNE, ÉLEVÉE, URGENTE
    machine_id = Column(Integer, nullable=False)  # US-CHETOP-003: Associated machine
    utilisateur_id = Column(Integer, nullable=True)  # US-CHETOP-005: Assigned user
    date_echeance = Column(
        DateTime(timezone=True), nullable=True
    )  # US-CHETOP-001: Due date
    statut = Column(
        SQLEnum(OrdreStatut), nullable=False, default=OrdreStatut.DRAFT
    )  # Full workflow: DRAFT → SUBMITTED → APPROVED → ASSIGNED → IN_PROGRESS → COMPLETED → VALIDATED → CLOSED
    created_by = Column(Integer, nullable=True)
    validated_by = Column(Integer, nullable=True)
    date_validation = Column(DateTime(timezone=True), nullable=True)
    estimated_duration = Column(Integer, nullable=True)
    date_debut = Column(DateTime(timezone=True), nullable=True)
    date_fin = Column(DateTime(timezone=True), nullable=True)
    rapport = Column(Text, nullable=True)
    failure_type = Column(String(100), nullable=True)
    cheftech_feedback = Column(Text, nullable=True)
    timer_started_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    archived_at = Column(DateTime(timezone=True), nullable=True)

    archive_reason = Column(String(50), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Post-maintenance recovery snapshots — unified_health_score captured at
    # WO creation (baseline) and just before completion (pre-fix state).
    # Used to compute delta vs current health for recovery classification.
    health_score_at_creation = Column(Float, nullable=True)
    health_score_at_completion = Column(Float, nullable=True)

    # Relationships for eager loading (no FK constraints in DB, use primaryjoin)
    machine = relationship(
        "Machines",
        primaryjoin="foreign(Ordres_travail.machine_id) == Machines.id",
        lazy="noload",
        viewonly=True,
    )
    utilisateur = relationship(
        "Utilisateurs",
        primaryjoin="foreign(Ordres_travail.utilisateur_id) == Utilisateurs.id",
        lazy="noload",
        viewonly=True,
    )
    interventions = relationship(
        "Ordres_intervention",
        primaryjoin="Ordres_travail.id == foreign(Ordres_intervention.ordre_travail_id)",
        lazy="noload",
        viewonly=True,
    )
    linked_alerts = relationship(
        "Alert",
        primaryjoin="Ordres_travail.id == foreign(Alert.work_order_id)",
        lazy="noload",
        viewonly=True,
    )
