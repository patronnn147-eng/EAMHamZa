"""
ChatSession service — DB-backed chat history, replaces in-memory CHAT_HISTORY dict.
"""
import logging
from typing import List, Dict, Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.chat_sessions import ChatSession

logger = logging.getLogger(__name__)

# Max messages kept per session (rolling window)
MAX_MESSAGES = 50


class ChatSessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, utilisateur_id: int) -> ChatSession:
        """Get the active session for a user, or create one."""
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.utilisateur_id == utilisateur_id)
            .order_by(ChatSession.updated_at.desc())
            .limit(1)
        )
        session = result.scalar_one_or_none()
        if not session:
            session = ChatSession(utilisateur_id=utilisateur_id, messages=[])
            self.db.add(session)
            await self.db.flush()
            logger.info(f"Created chat session for user {utilisateur_id}")
        return session

    async def get_history(
        self,
        utilisateur_id: int,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Return last N messages for a user."""
        session = await self.get_or_create(utilisateur_id)
        messages = session.messages or []
        return messages[-limit:]

    async def append_messages(
        self,
        utilisateur_id: int,
        new_messages: List[Dict[str, str]],
    ) -> None:
        """
        Append new messages to the session.
        Rolls the window to MAX_MESSAGES to prevent unbounded growth.
        """
        try:
            session = await self.get_or_create(utilisateur_id)
            current: List = list(session.messages or [])
            current.extend(new_messages)

            # Rolling window
            if len(current) > MAX_MESSAGES:
                current = current[-MAX_MESSAGES:]

            session.messages = current
            session.message_count = len(current)

            # Track last user query for /history endpoint
            user_msgs = [m for m in new_messages if m.get("role") == "user"]
            if user_msgs:
                session.last_query = user_msgs[-1].get("content", "")[:500]

            from datetime import datetime
            session.updated_at = datetime.utcnow()

            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error appending chat messages: {e}")
            raise

    async def get_session_info(self, utilisateur_id: int) -> Dict[str, Any]:
        """Summary for /history endpoint."""
        session = await self.get_or_create(utilisateur_id)
        messages = session.messages or []
        return {
            "session_id": str(session.id),
            "message_count": len(messages),
            "last_query": session.last_query,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
            "history": messages[-20:],
            "total": len(messages),
        }

    async def clear(self, utilisateur_id: int) -> None:
        """Clear history for a user (optional reset endpoint)."""
        try:
            session = await self.get_or_create(utilisateur_id)
            session.messages = []
            session.message_count = 0
            session.last_query = None
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error clearing chat session: {e}")
            raise
