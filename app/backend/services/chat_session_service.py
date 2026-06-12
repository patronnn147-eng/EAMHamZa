"""
ChatSession service — DB-backed multi-conversation history.

Supports multiple conversations per user. Each ChatSession row is one
independent conversation with its own messages, title, and timestamps.

Backward-compatible helpers (`get_or_create`, `get_history(user_id)`) keep
existing callers working — they target the user's most-recent session.
New helpers (`list_for_user`, `create`, `get_by_id`, `delete`, `rename`)
power the multi-conversation sidebar.
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.chat_sessions import ChatSession

logger = logging.getLogger(__name__)

# Max messages kept per session (rolling window).
MAX_MESSAGES = 50

# Max char length of an auto-derived title (from first user message).
TITLE_MAX = 60


def _auto_title(text: str) -> str:
    """Build a short title from the first user message."""
    clean = " ".join(text.split())  # collapse whitespace
    if len(clean) <= TITLE_MAX:
        return clean or "Nouvelle conversation"
    return clean[: TITLE_MAX - 1].rstrip() + "…"


class ChatSessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Multi-session API (sidebar)
    # ------------------------------------------------------------------

    async def list_for_user(self, utilisateur_id: int) -> List[Dict[str, Any]]:
        """All sessions for a user, newest first. Lightweight summary only."""
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.utilisateur_id == utilisateur_id)
            .order_by(ChatSession.updated_at.desc())
        )
        sessions = result.scalars().all()
        return [
            {
                "id": str(s.id),
                "title": s.title or _auto_title(s.last_query or "Nouvelle conversation"),
                "message_count": s.message_count or 0,
                "last_query": s.last_query,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in sessions
        ]

    async def create(self, utilisateur_id: int, title: Optional[str] = None) -> ChatSession:
        """Create a fresh empty session and return it."""
        session = ChatSession(
            utilisateur_id=utilisateur_id,
            title=title or "Nouvelle conversation",
            messages=[],
            message_count=0,
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        logger.info(f"Created chat session {session.id} for user {utilisateur_id}")
        return session

    async def get_by_id(
        self, session_id: UUID, utilisateur_id: int
    ) -> Optional[ChatSession]:
        """Fetch a session, verifying ownership. Returns None if not found or not owned."""
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .where(ChatSession.utilisateur_id == utilisateur_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, session_id: UUID, utilisateur_id: int) -> bool:
        """Delete a session. Returns True if deleted, False if not found/not owned."""
        session = await self.get_by_id(session_id, utilisateur_id)
        if session is None:
            return False
        await self.db.delete(session)
        await self.db.commit()
        return True

    async def rename(
        self, session_id: UUID, utilisateur_id: int, title: str
    ) -> Optional[ChatSession]:
        """Rename a session. Returns updated session or None if not found/not owned."""
        session = await self.get_by_id(session_id, utilisateur_id)
        if session is None:
            return None
        session.title = title.strip()[:200] or "Conversation"
        session.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(session)
        return session

    # ------------------------------------------------------------------
    # Per-session message ops (used by the chat endpoint)
    # ------------------------------------------------------------------

    async def get_history_by_session(
        self,
        session_id: UUID,
        utilisateur_id: int,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Last N messages for a specific session (ownership-checked)."""
        session = await self.get_by_id(session_id, utilisateur_id)
        if session is None:
            return []
        messages = session.messages or []
        return messages[-limit:]

    async def append_to_session(
        self,
        session_id: UUID,
        utilisateur_id: int,
        new_messages: List[Dict[str, str]],
    ) -> Optional[ChatSession]:
        """Append messages to a specific session (ownership-checked)."""
        try:
            session = await self.get_by_id(session_id, utilisateur_id)
            if session is None:
                return None

            current: List = list(session.messages or [])
            current.extend(new_messages)
            if len(current) > MAX_MESSAGES:
                current = current[-MAX_MESSAGES:]
            session.messages = current
            session.message_count = len(current)

            user_msgs = [m for m in new_messages if m.get("role") == "user"]
            if user_msgs:
                first_user = user_msgs[-1].get("content", "")
                session.last_query = first_user[:500]
                # Auto-set title from first user message if still default/empty
                if not session.title or session.title in ("Nouvelle conversation", "Conversation"):
                    session.title = _auto_title(first_user)

            session.updated_at = datetime.utcnow()
            await self.db.commit()
            return session
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error appending chat messages to session {session_id}: {e}")
            raise

    # ------------------------------------------------------------------
    # Backward-compat (single-session) helpers — target user's most-recent
    # ------------------------------------------------------------------

    async def get_or_create(self, utilisateur_id: int) -> ChatSession:
        """Get the most-recent session for a user, or create a fresh one."""
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.utilisateur_id == utilisateur_id)
            .order_by(ChatSession.updated_at.desc())
            .limit(1)
        )
        session = result.scalar_one_or_none()
        if session is None:
            session = await self.create(utilisateur_id)
        return session

    async def get_history(
        self,
        utilisateur_id: int,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Last N messages for the user's most-recent session."""
        session = await self.get_or_create(utilisateur_id)
        messages = session.messages or []
        return messages[-limit:]

    async def append_messages(
        self,
        utilisateur_id: int,
        new_messages: List[Dict[str, str]],
    ) -> None:
        """Backward-compat append to most-recent session."""
        session = await self.get_or_create(utilisateur_id)
        await self.append_to_session(session.id, utilisateur_id, new_messages)

    async def get_session_info(self, utilisateur_id: int) -> Dict[str, Any]:
        """Summary for /history endpoint (single-session legacy shape)."""
        session = await self.get_or_create(utilisateur_id)
        messages = session.messages or []
        return {
            "session_id": str(session.id),
            "title": session.title or "Nouvelle conversation",
            "message_count": len(messages),
            "last_query": session.last_query,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
            "history": messages[-20:],
            "total": len(messages),
        }

    async def clear(self, utilisateur_id: int) -> None:
        """Wipe messages on user's most-recent session (not delete the row)."""
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
