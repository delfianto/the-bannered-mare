"""Data access layer for ModelFamily entities"""

from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import any_, func, select
from sqlalchemy.orm import Session

from src.core.persistence import BaseRepository
from src.model_family.models import ModelFamily


class ModelFamilyRepository(BaseRepository[ModelFamily]):
    """Repository for ModelFamily data access with custom queries"""

    def __init__(self, db: Session):
        """Initialize ModelFamily repository"""
        super().__init__(db, ModelFamily)

    def find_paginated_with_count(
        self,
        limit: int = BaseRepository.DEFAULT_LIMIT,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[ModelFamily], int]:
        """Get model families with pagination and filtering"""
        if limit > self.MAX_LIMIT:
            raise ValueError(f"Limit cannot exceed {self.MAX_LIMIT}")

        # provider_type matches against the provider_types ARRAY, so it can't go
        # through the generic column-operator filter — handle it separately.
        remaining = dict(filters or {})
        provider_type = remaining.pop("provider_type", None)

        stmt = select(ModelFamily)
        stmt = self._apply_filters(stmt, remaining)
        if provider_type:
            stmt = stmt.where(cast(Any, provider_type == any_(ModelFamily.provider_types)))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()

        # Default to case-insensitive name ordering so the list is alphabetical
        # and pagination is deterministic; id breaks ties for duplicate names.
        stmt = (
            stmt.order_by(func.lower(ModelFamily.name), ModelFamily.id).limit(limit).offset(offset)
        )
        items = list(self.db.execute(stmt).scalars().all())

        return items, total

    def find_first(self) -> ModelFamily | None:
        """Return any one family (name-ordered for determinism), or None if none exist."""
        stmt = select(ModelFamily).order_by(func.lower(ModelFamily.name), ModelFamily.id).limit(1)
        return self.db.execute(stmt).scalars().first()

    def find_by_name(self, name: str) -> ModelFamily | None:
        """
        Find a model family by name.

        Args:
            name: The unique family name to search for

        Returns:
            The model family if found, None otherwise
        """
        stmt = select(ModelFamily).where(ModelFamily.name == name)
        return self.db.execute(stmt).scalars().first()

    def search_by_name(self, name: str) -> Sequence[ModelFamily]:
        """
        Search for model families by name (case-insensitive partial match).

        Args:
            name: The name fragment to search for

        Returns:
            Sequence of matching model families
        """
        stmt = select(ModelFamily).where(ModelFamily.name.ilike(f"%{name}%"))
        return list(self.db.execute(stmt).scalars().all())

    def find_by_identifier(self, family_identifier: str) -> ModelFamily | None:
        """
        Find a model family by its identifier.

        Args:
            family_identifier: The family identifier to search for

        Returns:
            ModelFamily if found, None otherwise
        """
        stmt = select(ModelFamily).where(ModelFamily.family_identifier == family_identifier)
        return self.db.execute(stmt).scalars().first()
