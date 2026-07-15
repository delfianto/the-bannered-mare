"""Data access layer for Chat entities"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import update
from sqlalchemy.orm import Session

from src.chat_session import queries
from src.chat_session.models import Chat
from src.core.pagination import DEFAULT_PAGE_SIZE
from src.core.persistence import BaseRepository

logger = logging.getLogger(__name__)


class ChatRepository(BaseRepository[Chat]):
    """Repository for Chat data access with custom queries"""

    def __init__(self, db: Session):
        """Initialize Chat repository"""
        super().__init__(db, Chat)

    def find_all_ordered(self, order_by: Any | None = None) -> list[Chat]:
        """Find all chats newest-first (eager-loads character; fixed ordering, so
        ``order_by`` is accepted for base-class compatibility but ignored)."""
        return list(self.db.execute(queries.all_ordered_stmt()).scalars().all())

    def find_by_id(self, entity_id: str) -> Chat | None:
        """Find chat by ID with eager loading of character"""
        return self.db.execute(queries.by_id_with_character_stmt(entity_id)).scalars().first()

    def find_bookmarked(self) -> list[Chat]:
        """Find all bookmarked chats, newest first."""
        return list(self.db.execute(queries.bookmarked_stmt()).scalars().all())

    def find_paginated_ordered(
        self,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
        order_by: Any | None = None,
    ) -> tuple[list[Chat], int]:
        """Find chats ordered by creation date with pagination and filtering.

        Uses a fixed ordered query (eager loads), so ``order_by`` is accepted for
        base-class compatibility but ignored."""
        if limit > self.MAX_LIMIT:
            raise ValueError(f"Limit cannot exceed {self.MAX_LIMIT}")

        count_stmt, page_stmt = queries.ordered_page_stmts(limit, offset, filters)
        total = self.db.execute(count_stmt).scalar_one()
        items = list(self.db.execute(page_stmt).scalars().all())
        return items, total

    def find_paginated_by_cursor(
        self,
        limit: int = DEFAULT_PAGE_SIZE,
        cursor: datetime | None = None,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[Chat], bool]:
        """
        Find chats ordered by updated_at desc using cursor pagination.
        Cursor is the 'updated_at' timestamp of the last item.
        """
        if limit > self.MAX_LIMIT:
            raise ValueError(f"Limit cannot exceed {self.MAX_LIMIT}")

        items = list(
            self.db.execute(queries.cursor_page_stmt(limit, cursor, filters)).scalars().all()
        )
        return queries.split_cursor_page(items, limit)

    def update_model_name_for_model_id(self, model_id: str, new_name: str) -> None:
        """Bulk update model_name for all chats using a specific model_id"""
        stmt = update(Chat).where(Chat.model_id == model_id).values(model_name=new_name)
        self.db.execute(stmt)

    def find_by_character_id(self, character_id: str) -> list[Chat]:
        """Find all chats for a specific character"""
        return list(self.db.execute(queries.by_character_stmt(character_id)).scalars().all())
