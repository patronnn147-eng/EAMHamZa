from core.database import Base
from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid


class AIMemories(Base):
    __tablename__ = "ai_memories"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=False, index=True)
    memory_type = Column(String(50), nullable=False)  # 'preference', 'strategy', 'failure'
    memory_key = Column(String(255), nullable=False)  # 'language', 'zone_preference', 'search_pattern'
    memory_value = Column(Text, nullable=False)  # 'French', 'Zone_North', 'machine_id + zone'
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    last_used = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)