"""Async data access layer for Message and MessageAlternative entities"""

from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.chat_message.models import Message
from src.core.persistence.base_repository_async import AsyncBaseRepository
from src.core.persistence.models import MessageAlternative

# Upper bound on messages loaded to build one prompt. The prompt builder already
# truncates history by token budget and lore/RAG only scan the last few turns, so
# only the newest messages ever matter. This caps an otherwise unbounded per-turn
# load on very long chats — realistic RP turns are 50-300 tokens, so 500 messages
# far exceeds any context window.
MAX_PROMPT_HISTORY = 500


class AsyncMessageAlternativeRepository(AsyncBaseRepository[MessageAlternative]):
    """Async repository for MessageAlternative data access"""

    def __init__(self, db: AsyncSession):
        super().__init__(db, MessageAlternative)

    async def find_by_message_id(self, message_id: str) -> list[MessageAlternative]:
        """Find all alternatives for a message, ordered by ordinal"""
        stmt = (
            select(MessageAlternative)
            .where(MessageAlternative.message_id == message_id)
            .order_by(MessageAlternative.ordinal.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_message_id(self, message_id: str) -> int:
        """Count alternatives for a message"""
        stmt = (
            select(func.count())
            .select_from(MessageAlternative)
            .where(MessageAlternative.message_id == message_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()


class AsyncMessageRepository(AsyncBaseRepository[Message]):
    """Async repository for Message data access with custom queries"""

    def __init__(self, db: AsyncSession):
        """Initialize async Message repository"""
        super().__init__(db, Message)

    async def find_by_chat_id(self, chat_id: str, limit: int = MAX_PROMPT_HISTORY) -> list[Message]:
        """Return the newest ``limit`` messages for a chat, chronological (ascending).

        Bounded because every caller builds a token-budgeted prompt or a
        recent-turns transcript from the tail of the history — never the whole log.
        """
        stmt = (
            select(Message)
            .where(Message.chat_id == chat_id)
            # id tie-breaker keeps the order total when messages share a created_at
            # (BE-M2) — otherwise same-instant rows sort arbitrarily.
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(reversed(list(result.scalars().all())))

    async def find_latest_by_chat_id(
        self,
        chat_id: str,
        limit: int,
        before: datetime | None = None,
        before_id: str | None = None,
    ) -> list[Message]:
        """
        Fetch latest messages for a chat, capable of 'scrolling back' in time.

        Args:
            chat_id: The chat ID.
            limit: Maximum number of messages to return.
            before: Cursor timestamp — only return messages created before it.
            before_id: Cursor id tie-breaker (BE-M2). With ``before``, forms a stable
                composite cursor ``(created_at, id)`` so rows sharing a ``created_at``
                are never skipped or duplicated across page boundaries. Omit it (legacy
                timestamp-only cursor) and same-instant boundary rows may be skipped.

        Returns:
            List of messages ordered newest to oldest, total order (created_at, id) desc.
        """
        # Apply Cursor: "Give me messages older than the bottom message I currently see."
        stmt = select(Message).where(Message.chat_id == chat_id)
        if before is not None and before_id is not None:
            stmt = stmt.where(
                or_(
                    Message.created_at < before,
                    and_(Message.created_at == before, Message.id < before_id),
                )
            )
        elif before is not None:
            stmt = stmt.where(Message.created_at < before)

        # Newest -> oldest, with an id tie-breaker so the order is total (BE-M2).
        stmt = stmt.order_by(Message.created_at.desc(), Message.id.desc())
        stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def find_by_id_in_chat(self, message_id: str, chat_id: str) -> Message | None:
        """Find a specific message by ID within a chat"""
        stmt = select(Message).where(Message.id == message_id, Message.chat_id == chat_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()
