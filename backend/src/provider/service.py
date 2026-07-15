"""Provider business logic service (entity CRUD).

Model discovery, caching, filtering, and the local-provider load/unload/delete
actions live in ``model_service.py``; this service owns only the provider entity
lifecycle.
"""

import re

from src.core.base_service import BaseCrudService, apply_update
from src.core.exceptions import ConflictError, ValidationError
from src.core.logging import get_logger
from src.core.persistence import UnitOfWork
from src.provider.models import Provider, ProviderType
from src.provider.repository import ProviderRepository

logger = get_logger(__name__)

_EDITABLE = {"name", "base_url", "api_key_env_var", "enabled"}


class ProviderService(BaseCrudService[Provider, ProviderRepository]):
    """Service for provider entity CRUD (inherits get_by_id)."""

    def __init__(self, provider_repo: ProviderRepository, uow: UnitOfWork | None = None):
        # Fallback keeps direct `ProviderService(...)` construction (tests) valid.
        super().__init__(provider_repo, uow or UnitOfWork(provider_repo.db), "Provider")

    def list_all(self) -> list[Provider]:
        """List all providers (insertion order)."""
        return self.repo.find_all()

    def create(
        self,
        name: str,
        provider_type: ProviderType,
        base_url: str | None = None,
        api_key_env_var: str | None = None,
    ) -> Provider:
        """Create a new provider"""
        if provider_type == ProviderType.CUSTOM:
            if not api_key_env_var:
                raise ValidationError("Custom providers must specify api_key_env_var")

            if not re.match(r"^[A-Z][A-Z0-9_]*$", api_key_env_var):
                raise ValidationError(
                    "Invalid api_key_env_var format. Must be uppercase with "
                    "underscores (e.g., MY_CUSTOM_API_KEY)"
                )

            if not base_url:
                raise ValidationError("Custom providers must specify base_url")

        elif api_key_env_var:
            raise ValidationError(
                f"Cannot specify api_key_env_var for {provider_type.value} provider. "
                f"This provider uses predefined environment variable"
            )

        existing = self.repo.find_by_name(name)
        if existing:
            raise ConflictError(f"Provider with name '{name}' already exists")

        provider = Provider(
            name=name,
            provider_type=provider_type,
            base_url=base_url,
            api_key_env_var=api_key_env_var,
        )

        created = self.repo.create(provider)
        self.uow.commit()

        if not created.has_api_key():
            env_var_name = created.get_env_var_name()
            logger.warning(
                f"Provider '{name}' created but API key not found. "
                + f"Set environment variable: {env_var_name}"
            )

        return created

    def update(
        self,
        provider_id: str,
        name: str | None = None,
        base_url: str | None = None,
        api_key_env_var: str | None = None,
        enabled: bool | None = None,
    ) -> Provider:
        """Update provider"""
        provider = self.get_by_id(provider_id)

        if api_key_env_var is not None:
            if provider.provider_type != ProviderType.CUSTOM:
                raise ValidationError(
                    f"Cannot update api_key_env_var for {provider.provider_type.value} "
                    f"provider. This provider uses predefined environment variable"
                )

            if not re.match(r"^[A-Z][A-Z0-9_]*$", api_key_env_var):
                raise ValidationError(
                    "Invalid api_key_env_var format. Must be uppercase with "
                    "underscores (e.g., MY_CUSTOM_API_KEY)"
                )

        patch = {
            "name": name,
            "base_url": base_url,
            "api_key_env_var": api_key_env_var,
            "enabled": enabled,
        }
        apply_update(provider, {k: v for k, v in patch.items() if v is not None}, _EDITABLE)

        updated = self.repo.update(provider)
        self.uow.commit()
        return updated

    def update_flags(self, provider_id: str, enabled: bool) -> Provider:
        """Update provider enabled/disabled state"""
        provider = self.get_by_id(provider_id)
        provider.enabled = enabled
        updated = self.repo.update(provider)
        self.uow.commit()

        logger.info(
            "provider_flags_updated",
            provider_id=provider_id,
            enabled=enabled,
        )
        return updated

    def delete(self, provider_id: str) -> None:
        """Providers cannot be deleted (referential integrity); disable instead.

        Raises a domain ``ConflictError`` (→ HTTP 409) rather than
        ``NotImplementedError`` so that, if ever routed, it maps cleanly through
        the global handler instead of surfacing as an unhandled 500.
        """
        raise ConflictError(
            "Providers cannot be deleted. Use update_flags to disable the provider instead."
        )
