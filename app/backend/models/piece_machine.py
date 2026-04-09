from core.database import Base
from sqlalchemy import Column, Integer, ForeignKey, Table

# Association table for many-to-many between Piece and Machine
piece_machine = Table(
    "piece_machine",
    Base.metadata,
    Column("piece_id", Integer, ForeignKey("pieces.id"), primary_key=True),
    Column("machine_id", Integer, ForeignKey("machines.id"), primary_key=True),
    extend_existing=True,
)
