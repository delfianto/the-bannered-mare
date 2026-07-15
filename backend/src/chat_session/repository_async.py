"""Async data access layer for Chat entities"""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.chat_session import queries
from src.chat_session.models import Chat
from src.core.persistence.base_repository_async import AsyncBaseRepository
from src.core.persistence.models import PromptTemplate, TemplateFragment
from src.model.models import ModelRegistry, ModelRoute


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
        The gateway resolves the model's *active route* for the provider +
        identifier, so that chain is eager-loaded as well.
        """
        stmt = (
            select(Chat)
            .where(Chat.id == chat_id)
            .options(
                joinedload(Chat.character),
                joinedload(Chat.model)
                .joinedload(ModelRegistry.active_route)
                .joinedload(ModelRoute.provider),
                joinedload(Chat.model).joinedload(ModelRegistry.model_family),
                joinedload(Chat.model)
                .joinedload(ModelRegistry.template)
                .selectinload(PromptTemplate.template_fragments)
                .joinedload(TemplateFragment.fragment),
                # Task model (auxiliary calls): its active route's provider AND its
                # model_family — the gateway resolves family-default params for it
                # too, so a missing family here lazy-loads and raises MissingGreenlet.
                joinedload(Chat.task_model)
                .joinedload(ModelRegistry.active_route)
                .joinedload(ModelRoute.provider),
                joinedload(Chat.task_model).joinedload(ModelRegistry.model_family),
                joinedload(Chat.template)
                .selectinload(PromptTemplate.template_fragments)
                .joinedload(TemplateFragment.fragment),
                joinedload(Chat.persona),
                joinedload(Chat.preset),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def find_all_ordered(self, order_by: Any | None = None) -> list[Chat]:
        """Find all chats newest-first (eager-loads character; fixed ordering, so
        ``order_by`` is accepted for base-class compatibility but ignored)."""
        result = await self.db.execute(queries.all_ordered_stmt())
        return list(result.scalars().all())

    async def find_paginated_ordered(
        self,
        limit: int = 10,
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
        total = (await self.db.execute(count_stmt)).scalar_one()
        items = list((await self.db.execute(page_stmt)).scalars().all())
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

        result = await self.db.execute(queries.cursor_page_stmt(limit, cursor, filters))
        return queries.split_cursor_page(list(result.scalars().all()), limit)

    async def find_by_character_id(self, character_id: str) -> list[Chat]:
        """Find all chats for a specific character"""
        result = await self.db.execute(queries.by_character_stmt(character_id))
        return list(result.scalars().all())
