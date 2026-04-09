from core.database import Base
from sqlalchemy import Column, Integer, ForeignKey, Float, DateTime
from sqlalchemy.sql import func

class Stock(Base):
    __tablename__ = "stock"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    piece_id = Column(Integer, ForeignKey("pieces.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
