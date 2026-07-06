"""Data access layer for Message entities"""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.chat_message.models import Message
from src.core.persistence import BaseRepository


class MessageRepository(BaseRepository[Message]):
    """Repository for Message data access with custom queries"""

    def __init__(self, db: Session):
        """Initialize Message repository"""
        super().__init__(db, Message)

    def find_by_chat_id(self, chat_id: str) -> list[Message]:
        """Find all messages for a specific chat ordered by creation date"""
        stmt = select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at.asc())
        return list(self.db.execute(stmt).scalars().all())

    def delete_by_chat_id(self, chat_id: str) -> None:
        """Delete all messages for a specific chat"""
        stmt = delete(Message).where(Message.chat_id == chat_id)
        self.db.execute(stmt)
        self.db.flush()
