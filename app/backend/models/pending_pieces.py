"""PendingPiece model — uncatalogued items submitted by technicians.

When a technician needs a piece that's not in the catalog (e.g., a generic
"M4 screw"), they submit it via the intervention dialog. A placeholder
mouvement_stock row is created IMMEDIATELY with movement_type='PENDING_OUT'
and pending_piece_id=this.id to preserve chronology. The created_at of that
movement row reflects the actual submission time, not the eventual review
time.

Admins later review the queue and either:
  - MATCHED   → link to existing piece (in-place mouvement_stock update)
  - CREATED   → create a brand-new piece, then link
  - REJECTED  → status only; placeholder mouvement_stock marked 'REJECTED'

Status transitions are one-way (no rollback) for audit integrity.
"""

from core.database import Base
from sqlalchemy import (
    Column,
    Integer,
    Numeric,
    String,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.sql import func

_SET_NULL = "SET NULL"


class PendingPiece(Base):
    __tablename__ = "pending_pieces"
    __table_args__ = {"extend_existing": True}

    id = Column(
        Integer, primary_key=True, index=True, autoincrement=True, nullable=False
    )
    intervention_id = Column(
        Integer,
        ForeignKey("OrdresIntervention.id", ondelete=_SET_NULL),
        nullable=True,
        index=True,
    )
    submitted_by = Column(
        Integer,
        ForeignKey("utilisateurs.id", ondelete=_SET_NULL),
        nullable=True,
    )
    name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=True)
    quantity = Column(Numeric(10, 2), nullable=False)
    unit = Column(String(20), nullable=False, default="pcs")
    photo_object_key = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="PENDING_REVIEW", index=True)
    matched_piece_id = Column(
        Integer,
        ForeignKey("pieces.id", ondelete=_SET_NULL),
        nullable=True,
    )
    reviewed_by = Column(
        Integer,
        ForeignKey("utilisateurs.id", ondelete=_SET_NULL),
        nullable=True,
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

