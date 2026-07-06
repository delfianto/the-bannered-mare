"""Data access layer for Chat entities"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, joinedload

from src.chat_session.models import Chat
from src.core.persistence import BaseRepository

logger = logging.getLogger(__name__)


class ChatRepository(BaseRepository[Chat]):
    """Repository for Chat data access with custom queries"""

    def __init__(self, db: Session):
        """Initialize Chat repository"""
        super().__init__(db, Chat)

    def find_all_ordered(self) -> list[Chat]:
        """Find all chats ordered by creation date"""
        stmt = select(Chat).options(joinedload(Chat.character)).order_by(Chat.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def find_by_id(self, entity_id: str) -> Chat | None:
        """Find chat by ID with eager loading of character"""
        stmt = select(Chat).options(joinedload(Chat.character)).where(Chat.id == entity_id)
        return self.db.execute(stmt).scalars().first()

    def find_paginated_ordered(
        self, limit: int = 10, offset: int = 0, filters: dict[str, Any] | None = None
    ) -> tuple[list[Chat], int]:
        """Find chats ordered by creation date with pagination and filtering"""
        if limit > self.MAX_LIMIT:
            raise ValueError(f"Limit cannot exceed {self.MAX_LIMIT}")

        stmt = select(Chat).options(joinedload(Chat.character))
        stmt = self._apply_filters(stmt, filters)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()

        stmt = stmt.order_by(Chat.created_at.desc()).limit(limit).offset(offset)
        items = list(self.db.execute(stmt).scalars().all())

        return items, total

    def find_paginated_by_cursor(
        self,
        limit: int = 20,
        cursor: datetime | None = None,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[Chat], bool]:
        """
        Find chats ordered by updated_at desc using cursor pagination.
        Cursor is the 'updated_at' timestamp of the last item.
        """
        if limit > self.MAX_LIMIT:
            raise ValueError(f"Limit cannot exceed {self.MAX_LIMIT}")

        stmt = select(Chat).options(joinedload(Chat.character))
        stmt = self._apply_filters(stmt, filters)

        if cursor:
            stmt = stmt.where(Chat.updated_at < cursor)

        # Order by updated_at desc
        stmt = stmt.order_by(Chat.updated_at.desc())

        # Limit + 1 to check next page
        stmt = stmt.limit(limit + 1)

        items = list(self.db.execute(stmt).scalars().all())

        has_more = False
        if len(items) > limit:
            has_more = True
            items = items[:limit]

        return items, has_more

    def update_model_name_for_model_id(self, model_id: str, new_name: str) -> None:
        """Bulk update model_name for all chats using a specific model_id"""
        stmt = update(Chat).where(Chat.model_id == model_id).values(model_name=new_name)
        self.db.execute(stmt)

    def find_by_character_id(self, character_id: str) -> list[Chat]:
        """Find all chats for a specific character"""
        stmt = select(Chat).where(Chat.character_id == character_id)
        return list(self.db.execute(stmt).scalars().all())
