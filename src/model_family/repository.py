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

        stmt = select(ModelFamily)
        stmt = self._apply_filters(stmt, filters)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()

        stmt = stmt.limit(limit).offset(offset)
        items = list(self.db.execute(stmt).scalars().all())

        return items, total

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

    def find_by_provider_type(self, provider_type: str) -> Sequence[ModelFamily]:
        """
        Find all model families for a specific provider type.

        Args:
            provider_type: The provider type to filter by (e.g., 'openai', 'anthropic')

        Returns:
            Sequence of model families for the provider
        """
        # Since provider_types is an ARRAY or JSON (depending on backend), we use a compatible filter
        stmt = select(ModelFamily).where(
            cast(Any, provider_type == any_(ModelFamily.provider_types))
        )
        return list(self.db.execute(stmt).scalars().all())

    def find_by_parameter_support(self, parameter_name: str) -> Sequence[ModelFamily]:
        """
        Find model families that define a specific parameter.

        Args:
            parameter_name: The parameter name to search for

        Returns:
            Sequence of model families supporting the parameter
        """
        # Check if the parameter exists in the 'parameters' JSON object
        stmt = select(ModelFamily).where(ModelFamily.parameters.has_key(parameter_name))
        return list(self.db.execute(stmt).scalars().all())
