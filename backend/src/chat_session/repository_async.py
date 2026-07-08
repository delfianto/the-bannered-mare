"""Async data access layer for Chat entities"""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.chat_session.models import Chat
from src.core.persistence.base_repository_async import AsyncBaseRepository
from src.core.persistence.models import PromptTemplate, TemplateFragment
from src.model.models import Model


class AsyncChatRepository(AsyncBaseRepository[Chat]):
    """Async repository for Chat data access with custom queries"""

    def __init__(self, db: AsyncSession):
        """Initialize async Chat repository"""
        super().__init__(db, Chat)

    async def find_by_id_with_relations(self, chat_id: str) -> Chat | None:
        """
        Find chat by ID with all relations eagerly loaded.

        This is CRITICAL for async to avoid lazy loading issues. The prompt
        builder walks template.template_fragments and each fragment, so those
        must be eager-loaded too (both for the chat's own template and the
        model's default template) or the async session raises MissingGreenlet.
        """
        stmt = (
            select(Chat)
            .where(Chat.id == chat_id)
            .options(
                joinedload(Chat.character),
                joinedload(Chat.model).joinedload(Model.provider),
                joinedload(Chat.model).joinedload(Model.model_family),
                joinedload(Chat.model)
                .joinedload(Model.template)
                .selectinload(PromptTemplate.template_fragments)
                .joinedload(TemplateFragment.fragment),
                # Task model (auxiliary calls) only needs its provider for the gateway.
                joinedload(Chat.task_model).joinedload(Model.provider),
                joinedload(Chat.template)
                .selectinload(PromptTemplate.template_fragments)
                .joinedload(TemplateFragment.fragment),
                joinedload(Chat.persona),
                joinedload(Chat.preset),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def find_all_ordered(self) -> list[Chat]:
        """Find all chats ordered by creation date"""
        stmt = select(Chat).options(joinedload(Chat.character)).order_by(Chat.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def find_paginated_ordered(
        self, limit: int = 10, offset: int = 0, filters: dict[str, Any] | None = None
    ) -> tuple[list[Chat], int]:
        """Find chats ordered by creation date with pagination and filtering"""
        if limit > self.MAX_LIMIT:
            raise ValueError(f"Limit cannot exceed {self.MAX_LIMIT}")

        stmt = select(Chat).options(joinedload(Chat.character))
        stmt = self._apply_filters(stmt, filters)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        stmt = stmt.order_by(Chat.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def find_paginated_by_cursor(
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
            # Fetch items OLDER (smaller timestamp) than the cursor
            stmt = stmt.where(Chat.updated_at < cursor)

        # Order by updated_at desc
        stmt = stmt.order_by(Chat.updated_at.desc())

        # Limit + 1 to check next page
        stmt = stmt.limit(limit + 1)

        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        has_more = False
        if len(items) > limit:
            has_more = True
            items = items[:limit]

        return items, has_more

    async def find_by_character_id(self, character_id: str) -> list[Chat]:
        """Find all chats for a specific character"""
        stmt = select(Chat).where(Chat.character_id == character_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
