"""Gated-approval request for a technician-proposed machine status change.

Created by WO completion (technicien or chetop), reviewed by CHEFTECH.
Only APPROVED writes to Machines.statut — see
modules/shared/services/machine_status_requests.py.
"""
from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String, Text, Enum as SQLEnum
from sqlalchemy.sql import func
import enum


class RequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class MachineStatusChangeRequest(Base):
    __tablename__ = "machine_status_change_requests"
    __table_args__ = {"extend_existing": True}

    id = Column(
        Integer, primary_key=True, index=True, autoincrement=True, nullable=False
    )
    machine_id = Column(Integer, nullable=False, index=True)
    from_status = Column(String(30), nullable=False)
    to_status = Column(String(30), nullable=False)
    status = Column(
        SQLEnum(RequestStatus, native_enum=False, length=20),
        nullable=False,
        default=RequestStatus.PENDING,
        index=True,
    )
    # native_enum=False: DB column is character varying (not a PG enum type).
    # Without this, SQLAlchemy casts params to ::requeststatus →
    # "varchar = requeststatus" → UndefinedFunctionError. Mirrors
    # OrdresTravail.statut in models/ordres_travail.py.
    source_intervention_id = Column(Integer, nullable=True)
    requested_by = Column(Integer, nullable=True)
    requested_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reviewed_by = Column(Integer, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_note = Column(Text, nullable=True)
