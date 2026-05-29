"""MouvementStock — audit log of every stock movement.

Movement types:
  in                    — stock added (delivery, return)
  out                   — stock consumed (intervention, scrap)
  RESERVED              — quantity reserved for an approved intervention
                          (does not change Stock.quantity but reduces
                          available_stock = quantity - sum(reserved))
  RESERVATION_RELEASED  — reservation cleared (intervention completed/cancelled
                          or reservation expired)
  PENDING_OUT           — placeholder for an uncatalogued piece used by a
                          technician; piece_id is NULL, pending_piece_id is set
  REJECTED              — pending piece review rejected (no stock change)

Either piece_id or pending_piece_id must be set (DB CHECK).
"""
from core.database import Base
from sqlalchemy import Column, Integer, Numeric, ForeignKey, String, DateTime
from sqlalchemy.sql import func


class MouvementStock(Base):
    __tablename__ = "mouvement_stock"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    # nullable now — pending pieces have no piece_id until resolved
    piece_id = Column(Integer, ForeignKey("pieces.id"), nullable=True)
    pending_piece_id = Column(
        Integer,
        ForeignKey("pending_pieces.id", ondelete="SET NULL"),
        nullable=True,
    )
    quantity = Column(Numeric(10, 2), nullable=False)
    unit = Column(String(20), nullable=False, default="pcs")
    movement_type = Column(String, nullable=False)
    reference = Column(String, nullable=True)
    intervention_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
