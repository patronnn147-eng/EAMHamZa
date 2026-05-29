from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum


class PlanningType(str, enum.Enum):
    """Planning types"""
    MAINTENANCE = "MAINTENANCE"
    SHIFT = "SHIFT"
    HEBDOMADAIRE = "HEBDOMADAIRE"
    MENSUEL = "MENSUEL"
    JOURNALIER = "JOURNALIER"


class PlanningStatut(str, enum.Enum):
    """Planning workflow status"""
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ShiftType(str, enum.Enum):
    """Shift types for SHIFT planning"""
    MORNING = "MORNING"
    NIGHT = "NIGHT"


class Plannings(Base):
    __tablename__ = "plannings"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    identifiant_planning = Column(String, nullable=False)
    date_debut = Column(DateTime(timezone=True), nullable=False)
    date_fin = Column(DateTime(timezone=True), nullable=False)
    type = Column(SQLEnum(PlanningType), nullable=False)
    shift_type = Column(SQLEnum(ShiftType), nullable=True)  # Only for SHIFT type
    planning_statut = Column(SQLEnum(PlanningStatut), nullable=False, default=PlanningStatut.DRAFT)  # DRAFT → SUBMITTED → APPROVED → REJECTED
    chef_operation_id = Column(Integer, nullable=True)  # CHETOP user
    chef_technique_id = Column(Integer, nullable=True)  # CHEFTECH user
    zone_travail = Column(String(100), nullable=True)  # Zone where team will work
    sous_zone = Column(String(100), nullable=True)
    ordre = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)

    archived_at = Column(DateTime(timezone=True), nullable=True)

    archive_reason = Column(String(50), nullable=True)

    # Relationships for eager loading (bridge tables)
    planning_utilisateurs = relationship(
        "Planning_utilisateurs",
        primaryjoin="Plannings.id == foreign(Planning_utilisateurs.planning_id)",
        lazy="noload",
        viewonly=True,
    )
    planning_machines = relationship(
        "Planning_machines",
        primaryjoin="Plannings.id == foreign(Planning_machines.planning_id)",
        lazy="noload",
        viewonly=True,
    )