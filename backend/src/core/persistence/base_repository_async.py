"""Generic async base repository for common CRUD operations"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.persistence.base_model import BaseModel
from src.core.persistence.statements import apply_filters


class AsyncBaseRepository[T: BaseModel]:
    """
    Generic async repository providing common CRUD operations.

    Type-safe base class for async database operations.
    Uses flush() instead of commit() to allow service layer
    to control transaction boundaries.
    """

    DEFAULT_LIMIT = 10
    MAX_LIMIT = 100

    def __init__(self, db: AsyncSession, model: type[T]):
        """
        Initialize async repository.

        Args:
            db: SQLAlchemy async session
            model: The SQLAlchemy model class this repository manages
        """
        self.db = db
        self.model = model

    def _apply_filters(self, stmt, filters: dict[str, Any] | None = None):
        """Apply ``{field__op: value}`` filters (see statements.apply_filters)."""
        return apply_filters(self.model, stmt, filters)

    async def find_by_id(self, entity_id: str) -> T | None:
        """
        Find entity by ID.

        Args:
            entity_id: The entity's unique identifier

        Returns:
            The entity if found, None otherwise
        """
        stmt = select(self.model).where(self.model.id == entity_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def find_all(self) -> list[T]:
        """Get ALL entities"""
        stmt = select(self.model)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def find_paginated_with_count(
        self, limit: int = DEFAULT_LIMIT, offset: int = 0
    ) -> tuple[list[T], int]:
        """Get entities with pagination and total count"""
        if limit > self.MAX_LIMIT:
            raise ValueError(f"Limit cannot exceed {self.MAX_LIMIT}")

        # Count query
        count_stmt = select(func.count()).select_from(self.model)
        total = await self.db.execute(count_stmt)
        total_count = total.scalar_one()

        # Items query
        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        return items, total_count

    async def create(self, entity: T) -> T:
        """
        Add a new entity to the database session.

        Uses flush() instead of commit() to allow the service layer
        to control transaction boundaries.

        Args:
            entity: The entity to create

        Returns:
            The created entity with generated ID and timestamps
        """
        # No refresh(): all defaults are Python-side, so flush() fully populates
        # the object (and avoids an expired-attribute lazy load, which would raise
        # under async). flush()'s own unit-of-work ordering handles any pending
        # changes, so no pre-flush guard is needed either.
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def update(self, entity: T) -> T:
        """
        Update existing entity in the session without committing.

        Args:
            entity: The entity to update

        Returns:
            The updated entity
        """
        await self.db.flush()
        return entity

    async def delete(self, entity: T) -> None:
        """
        Mark an entity for removal from the database.

        Args:
            entity: The entity to remove
        """
        await self.db.delete(entity)
        await self.db.flush()

    async def count(self) -> int:
        """Get the total count of entities"""
        stmt = select(func.count()).select_from(self.model)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def exists(self, entity_id: str) -> bool:
        """
        Check if an entity exists by ID.

        Args:
            entity_id: The entity's unique identifier

        Returns:
            True if the entity exists, False otherwise
        """
        stmt = select(self.model.id).where(self.model.id == entity_id)
        result = await self.db.execute(stmt)
        return result.first() is not None

    async def commit(self) -> None:
        """
        Commit the current transaction.

        This allows the service layer to control transaction boundaries
        without directly accessing the database session.
        """
        await self.db.commit()

    async def refresh(self, entity: T) -> T:
        """
        Refresh entity state from the database.

        Args:
            entity: The entity to refresh

        Returns:
            The refreshed entity
        """
        await self.db.refresh(entity)
        return entity

    async def rollback(self) -> None:
        """
        Perform rollback for the current transaction.

        Useful for error handling in the service layer.
        """
        await self.db.rollback()
