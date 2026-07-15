"""Data access layer for Message entities"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.chat_message.models import Message
from src.core.persistence import BaseRepository


class MessageRepository(BaseRepository[Message]):
    """Repository for Message data access with custom queries"""

    def __init__(self, db: Session):
        """Initialize Message repository"""
        super().__init__(db, Message)

    def find_all_by_chat_id(self, chat_id: str) -> list[Message]:
        """Return ALL messages for a chat, ascending by creation date (unbounded).

        Distinct from the async ``AsyncMessageRepository.find_by_chat_id``, which
        caps to the newest ``MAX_PROMPT_HISTORY`` for prompt building — this loads
        the full history, so use it only where every message is genuinely required.
        """
        stmt = select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at.asc())
        return list(self.db.execute(stmt).scalars().all())
