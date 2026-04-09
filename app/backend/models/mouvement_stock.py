from core.database import Base
from sqlalchemy import Column, Integer, ForeignKey, String, DateTime
from sqlalchemy.sql import func

class MouvementStock(Base):
    __tablename__ = "mouvement_stock"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    piece_id = Column(Integer, ForeignKey("pieces.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    movement_type = Column(String, nullable=False)  # 'in' or 'out'
    reference = Column(String, nullable=True)  # optional reference (e.g., order number)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
