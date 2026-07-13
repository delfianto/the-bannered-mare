"""Generic base repository for common CRUD operations"""

from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from src.core.persistence.base_model import BaseModel
from src.core.persistence.statements import apply_filters


class BaseRepository[T: BaseModel]:
    """
    Generic repository providing common CRUD operations.

    Type-safe base class that can be extended for specific models.
    Follows the repository pattern with flush() instead of commit()
    to allow service layer to control transaction boundaries.
    """

    DEFAULT_LIMIT = 10
    MAX_LIMIT = 100

    def __init__(self, db: Session, model: type[T]):
        """
        Initialize repository.

        Args:
            db: SQLAlchemy database session
            model: The SQLAlchemy model class this repository manages
        """
        self.db = db
        self.model = model

    def _apply_filters(self, stmt, filters: dict[str, Any] | None = None):
        """Apply ``{field__op: value}`` filters (see statements.apply_filters)."""
        return apply_filters(self.model, stmt, filters)

    def _column(self, name: str) -> Any:
        """Resolve a model column by name for generic queries on columns the
        ``BaseModel`` bound doesn't declare (e.g. ``name``/``is_default`` used by
        the mixins below). Mirrors the dynamic access ``apply_filters`` already does."""
        return getattr(self.model, name)

    def find_by_id(self, entity_id: str) -> T | None:
        """
        Find entity by ID.

        Args:
            entity_id: The entity's unique identifier

        Returns:
            The entity if found, None otherwise
        """
        stmt = select(self.model).where(self.model.id == entity_id)
        return self.db.execute(stmt).scalars().first()

    def find_all(self) -> list[T]:
        """Get ALL entities"""
        stmt = select(self.model)
        return list(self.db.execute(stmt).scalars().all())

    def find_paginated(self, limit: int = DEFAULT_LIMIT, offset: int = 0) -> list[T]:
        """Get entities with pagination"""
        if limit > self.MAX_LIMIT:
            raise ValueError(f"Limit cannot exceed {self.MAX_LIMIT}")

        stmt = select(self.model).limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())

    def find_paginated_with_count(
        self, limit: int = DEFAULT_LIMIT, offset: int = 0
    ) -> tuple[list[T], int]:
        """Get entities with pagination and total count"""
        if limit > self.MAX_LIMIT:
            raise ValueError(f"Limit cannot exceed {self.MAX_LIMIT}")

        count_stmt = select(func.count()).select_from(self.model)
        total = self.db.execute(count_stmt).scalar_one()

        stmt = select(self.model).limit(limit).offset(offset)
        items = list(self.db.execute(stmt).scalars().all())

        return items, total

    def find_all_ordered(self, order_by: Any | None = None) -> list[T]:
        """All entities, newest-first by default (``created_at`` desc)."""
        ordering = order_by if order_by is not None else self.model.created_at.desc()
        stmt = select(self.model).order_by(ordering)
        return list(self.db.execute(stmt).scalars().all())

    def find_paginated_ordered(
        self,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
        order_by: Any | None = None,
    ) -> tuple[list[T], int]:
        """Ordered, filtered pagination + total count. Defaults to ``created_at`` desc."""
        if limit > self.MAX_LIMIT:
            raise ValueError(f"Limit cannot exceed {self.MAX_LIMIT}")

        stmt = self._apply_filters(select(self.model), filters)
        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

        ordering = order_by if order_by is not None else self.model.created_at.desc()
        items = list(
            self.db.execute(stmt.order_by(ordering).limit(limit).offset(offset)).scalars().all()
        )
        return items, total

    def create(self, entity: T) -> T:
        """
        Add a new entity to the database session.

        Uses flush() instead of commit() to allow the service layer
        to control transaction boundaries. The entity is added to the
        session and flushed, making it visible within the current transaction,
        but not yet persisted to the database.

        Useful for:
        - Batching multiple operations before committing
        - Getting auto-generated IDs before commit
        - Validating constraints before final commit

        Args:
            entity: The entity to create

        Returns:
            The created entity with generated ID and timestamps (not yet persisted)
        """
        self.db.add(entity)
        self.db.flush()
        self.db.refresh(entity)
        return entity

    def update(self, entity: T) -> T:
        """
        Update existing entity in the session without committing.

        Uses flush() to persist changes to the database transaction but
        does not commit. The service layer controls when to commit.

        Args:
            entity: The entity to update

        Returns:
            The updated and refreshed entity (not yet committed)
        """
        self.db.flush()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: T) -> None:
        """
        Mark an entity for removal from the database.

        Uses flush() to mark for deletion without committing.
        The service layer controls when to commit.

        Args:
            entity: The entity to remove

        Example:
            family = repo.find_by_id("123")
            repo.delete(family)
            # Entity marked for deletion, but not yet committed
            repo.commit()  # Now it's deleted
        """
        self.db.delete(entity)
        self.db.flush()

    def count(self) -> int:
        """Get the total count of entities"""
        stmt = select(func.count()).select_from(self.model)
        return self.db.execute(stmt).scalar_one()

    def exists(self, entity_id: str) -> bool:
        """
        Check if an entity exists by ID.

        Args:
            entity_id: The entity's unique identifier

        Returns:
            True if the entity exists, False otherwise
        """
        stmt = select(self.model.id).where(self.model.id == entity_id)
        return self.db.execute(stmt).first() is not None

    def commit(self) -> None:
        """
        Commit the current transaction.

        This allows the service layer to control transaction boundaries
        without directly accessing the database session.
        """
        self.db.commit()

    def refresh(self, entity: T) -> T:
        """
        Refresh entity state from the database.

        Args:
            entity: The entity to refresh

        Returns:
            The refreshed entity
        """
        self.db.refresh(entity)
        return entity

    def rollback(self) -> None:
        """
        Perform rollback for the current transaction.

        Useful for error handling in the service layer.
        """
        self.db.rollback()


class NamedRepository[T: BaseModel](BaseRepository[T]):
    """Mixin for repositories whose model has a unique ``name`` column."""

    def find_by_name(self, name: str) -> T | None:
        """Find an entity by its unique ``name``."""
        stmt = select(self.model).where(self._column("name") == name)
        return self.db.execute(stmt).scalars().first()


class DefaultableRepository[T: BaseModel](BaseRepository[T]):
    """Mixin for repositories whose model has a boolean ``is_default`` column."""

    def unset_all_defaults(self, exclude_id: str | None = None) -> None:
        """Clear ``is_default`` on all rows, optionally excluding one by id."""
        stmt = update(self.model).where(self._column("is_default")).values({"is_default": False})
        if exclude_id:
            stmt = stmt.where(self.model.id != exclude_id)
        self.db.execute(stmt)
        self.db.flush()

    def set_default(self, entity_id: str) -> None:
        """Make ``entity_id`` the sole default row (clear the others, set this one)."""
        self.unset_all_defaults(exclude_id=entity_id)
        self.db.execute(
            update(self.model).where(self.model.id == entity_id).values({"is_default": True})
        )
        self.db.flush()
