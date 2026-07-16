"""ConsumedPiece model — actual piece consumption recorded at WO completion.

One row per piece consumed during an intervention.
- quantity_used     = actually consumed (counted as 'out' stock movement)
- quantity_wasted   = ruined/scrapped (also 'out' — but tracked separately
                      for loss accounting)
- quantity_returned = unused, returned to stock ('in' movement)
The sum (used + returned + wasted) must be <= required_piece.quantity_planned
(enforced by trg_consumed_le_planned trigger in DB).

Disposition is a human-readable summary tag:
  used        — fully used (typical default)
  partial     — partial use; used/returned/wasted detail filled in
  not_used    — reserved but not consumed
  wasted      — ruined entirely (e.g., dropped, damaged on install)
  returned    — returned to stock unused
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


class ConsumedPiece(Base):
    __tablename__ = "consumed_pieces"
    __table_args__ = {"extend_existing": True}

    id = Column(
        Integer, primary_key=True, index=True, autoincrement=True, nullable=False
    )
    intervention_id = Column(
        Integer,
        ForeignKey("OrdresIntervention.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    required_piece_id = Column(
        Integer,
        ForeignKey("required_pieces.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    piece_id = Column(
        Integer,
        ForeignKey("pieces.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity_used = Column(Numeric(10, 2), nullable=False, default=0)
    quantity_returned = Column(Numeric(10, 2), nullable=False, default=0)
    quantity_wasted = Column(Numeric(10, 2), nullable=False, default=0)
    unit = Column(String(20), nullable=False, default="pcs")
    disposition = Column(String(20), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
