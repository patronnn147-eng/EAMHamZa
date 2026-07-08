"""RequiredPiece model — pieces planned for a specific intervention.

A required_piece row carries:
- the planned quantity (set at intervention request time)
- the reserved quantity (set when CHEFTECH approves the request)
- an expiration date for the reservation (auto-released by Celery beat)
- an approval flag (NULL = pending, True = approved, False = rejected)

Quantities use Numeric(10,2) so consumables (oil, grease, cable) can use
fractional units. CHECK constraints enforced at DB level — see migration.
"""

from core.database import Base
from sqlalchemy import (
    Column,
    Integer,
    Numeric,
    String,
    Boolean,
    DateTime,
    ForeignKey,
)
from sqlalchemy.sql import func


class RequiredPiece(Base):
    __tablename__ = "required_pieces"
    __table_args__ = {"extend_existing": True}

    id = Column(
        Integer, primary_key=True, index=True, autoincrement=True, nullable=False
    )
    intervention_id = Column(
        Integer,
        ForeignKey("ordres_intervention.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    piece_id = Column(
        Integer,
        ForeignKey("pieces.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity_planned = Column(Numeric(10, 2), nullable=False)
    unit = Column(String(20), nullable=False, default="pcs")
    quantity_reserved = Column(Numeric(10, 2), nullable=False, default=0)
    reservation_expires_at = Column(DateTime(timezone=True), nullable=True)
    approved = Column(Boolean, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
