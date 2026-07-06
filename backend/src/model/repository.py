"""Data access layer for Model entities"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.persistence import BaseRepository
from src.model.models import Model


class ModelRepository(BaseRepository[Model]):
    """Repository for Model data access with custom queries"""

    def __init__(self, db: Session):
        """Initialize Model repository"""
        super().__init__(db, Model)

    def find_paginated_with_count(
        self,
        limit: int = BaseRepository.DEFAULT_LIMIT,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[Model], int]:
        """Get models with pagination and filtering"""
        if limit > self.MAX_LIMIT:
            raise ValueError(f"Limit cannot exceed {self.MAX_LIMIT}")

        stmt = select(Model)
        stmt = self._apply_filters(stmt, filters)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()

        # Default to case-insensitive name ordering so the list is alphabetical
        # and pagination is deterministic; id breaks ties for duplicate names.
        stmt = stmt.order_by(func.lower(Model.name), Model.id).limit(limit).offset(offset)
        items = list(self.db.execute(stmt).scalars().all())

        return items, total

    def find_by_identifier(self, provider_id: str, model_identifier: str) -> Model | None:
        """
        Find a model by provider ID and model identifier.

        Args:
            provider_id: The provider ID
            model_identifier: The model identifier to search for

        Returns:
            Model if found, None otherwise
        """
        stmt = select(Model).where(
            Model.provider_id == provider_id, Model.model_identifier == model_identifier
        )
        return self.db.execute(stmt).scalars().first()

    def find_by_provider(self, provider_id: str) -> list[Model]:
        """Find all models for a specific provider"""
        stmt = select(Model).where(Model.provider_id == provider_id)
        return list(self.db.execute(stmt).scalars().all())

    def find_enabled(self) -> list[Model]:
        """Find all enabled models"""
        stmt = select(Model).where(Model.enabled)
        return list(self.db.execute(stmt).scalars().all())

    def search_by_name(self, name: str) -> list[Model]:
        """
        Search for models by name (case-insensitive partial match).

        Args:
            name: The name fragment to search for

        Returns:
            List of matching models
        """
        stmt = select(Model).where(Model.name.ilike(f"%{name}%"))
        return list(self.db.execute(stmt).scalars().all())
