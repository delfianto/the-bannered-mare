"""Model Family business logic service"""

from typing import Any

from src.core.base_service import get_or_404
from src.core.exceptions import ConflictError
from src.core.logging import get_logger
from src.model_family.models import ModelFamily
from src.model_family.repository import ModelFamilyRepository
from src.model_family.schemas import ModelFamilyCreate, ModelFamilyUpdate

logger = get_logger(__name__)


class ModelFamilyService:
    """Service for model-family-related business logic"""

    def __init__(self, family_repo: ModelFamilyRepository):
        self.family_repo = family_repo

    def list_all(self) -> list[ModelFamily]:
        """List all model families"""
        return self.family_repo.find_all()

    def list_paginated(
        self, limit: int = 10, offset: int = 0, filters: dict[str, Any] | None = None
    ) -> tuple[list[ModelFamily], int]:
        """List model families with pagination and filtering"""
        return self.family_repo.find_paginated_with_count(limit, offset, filters=filters)

    def get_by_id(self, family_id: str) -> ModelFamily:
        """Get model family details by ID, raise 404 if not found"""
        return get_or_404(self.family_repo, family_id, "Model family")

    def create(self, family_data: ModelFamilyCreate) -> ModelFamily:
        """Create a new model family"""
        existing = self.family_repo.find_by_name(family_data.name)
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

        created = self.family_repo.create(family)
        self.family_repo.commit()
        return created

    def update(self, family_id: str, family_data: ModelFamilyUpdate) -> ModelFamily:
        """Update model family"""
        family = self.get_by_id(family_id)

        if family_data.name is not None:
            family.name = family_data.name
        if family_data.family_identifier is not None:
            family.family_identifier = family_data.family_identifier
        if family_data.description is not None:
            family.description = family_data.description
        if family_data.provider_types is not None:
            family.provider_types = family_data.provider_types
        if family_data.parameters is not None:
            family.parameters = family_data.parameters
        if family_data.unsupported_parameters is not None:
            family.unsupported_parameters = family_data.unsupported_parameters
        if family_data.extra_metadata is not None:
            family.extra_metadata = family_data.extra_metadata

        updated = self.family_repo.update(family)
        self.family_repo.commit()
        return updated

    def delete(self, family_id: str) -> None:
        """Delete model family"""
        family = self.get_by_id(family_id)

        if family.models:
            raise ConflictError(
                f"Cannot delete model family '{family.name}' because it is being used by "
                f"{len(family.models)} model(s)"
            )

        self.family_repo.delete(family)
        self.family_repo.commit()
