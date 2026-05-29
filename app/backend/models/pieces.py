from core.database import Base
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean
from sqlalchemy.sql import func

class Piece(Base):
    __tablename__ = "pieces"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    reference = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    unit_price = Column(Float, nullable=True)
    category = Column(String, nullable=True)
    min_stock = Column(Integer, nullable=True, default=5)
    # New columns for inventory consumption workflow
    is_consumable = Column(Boolean, nullable=False, default=False)
    default_unit = Column(String(20), nullable=False, default="pcs")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
