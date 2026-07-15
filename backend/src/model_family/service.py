"""Model Family business logic service"""

from typing import Any

from src.core.base_service import BaseCrudService, apply_update
from src.core.exceptions import ConflictError
from src.core.logging import get_logger
from src.core.pagination import DEFAULT_PAGE_SIZE
from src.core.persistence import UnitOfWork
from src.model_family.models import ModelFamily
from src.model_family.repository import ModelFamilyRepository
from src.model_family.schemas import ModelFamilyCreate, ModelFamilyUpdate

logger = get_logger(__name__)

_EDITABLE = {
    "name",
    "family_identifier",
    "description",
    "provider_types",
    "parameters",
    "unsupported_parameters",
    "extra_metadata",
}


class ModelFamilyService(BaseCrudService[ModelFamily, ModelFamilyRepository]):
    """Service for model-family-related business logic."""

    def __init__(self, family_repo: ModelFamilyRepository, uow: UnitOfWork | None = None):
        super().__init__(family_repo, uow or UnitOfWork(family_repo.db), "Model family")

    def list_all(self) -> list[ModelFamily]:
        """List all model families (insertion order)."""
        return self.repo.find_all()

    def list_paginated(
        self, limit: int = DEFAULT_PAGE_SIZE, offset: int = 0, filters: dict[str, Any] | None = None
    ) -> tuple[list[ModelFamily], int]:
        """List model families with pagination and filtering"""
        return self.repo.find_paginated_with_count(limit, offset, filters=filters)

    def get_first(self) -> ModelFamily | None:
        """Return any one family (name-ordered), or None if none exist.

        A discovery fallback (BE-H2): when an auto-created model matches no family
        by identifier, the caller falls back to any configured one and lets the user
        correct it afterward.
        """
        return self.repo.find_first()

    def create(self, family_data: ModelFamilyCreate) -> ModelFamily:
        """Create a new model family"""
        existing = self.repo.find_by_name(family_data.name)
        if existing:
            raise ConflictError(f"Model family with name '{family_data.name}' already exists")

        family = ModelFamily(
            name=family_data.name,
            family_identifier=family_data.family_identifier,
            description=family_data.description,
            provider_types=family_data.provider_types,
            parameters=family_data.parameters,
            unsupported_parameters=family_data.unsupported_parameters,
            extra_metadata=family_data.extra_metadata,
        )

        created = self.repo.create(family)
        self.uow.commit()
        return created

    def update(self, family_id: str, family_data: ModelFamilyUpdate) -> ModelFamily:
        """Update model family (skip-on-None: only provided fields change)."""
        family = self.get_by_id(family_id)
        apply_update(family, family_data.model_dump(exclude_none=True), _EDITABLE)
        updated = self.repo.update(family)
        self.uow.commit()
        return updated

    def delete(self, family_id: str) -> None:
        """Delete model family, unless models still reference it."""
        family = self.get_by_id(family_id)

        if family.models:
            raise ConflictError(
                f"Cannot delete model family '{family.name}' because it is being used by "
                f"{len(family.models)} model(s)"
            )

        self.repo.delete(family)
        self.uow.commit()
