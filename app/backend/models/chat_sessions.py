"""
ChatSession model — persists per-user conversation history in DB.
Replaces the in-memory CHAT_HISTORY dict.
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
import uuid

from core.database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    utilisateur_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=False, index=True)
    # Full message list stored as JSONB: [{"role": "user"|"assistant", "content": "..."}]
    messages = Column(JSONB, nullable=False, default=list)
    # Last query summary for quick display in history endpoint
    last_query = Column(Text, nullable=True)
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
