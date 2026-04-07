"""Provider business logic service"""

import re

from fastapi import HTTPException, status

from src.core.logging import get_logger
from src.provider.models import Provider, ProviderType
from src.provider.repository import ProviderRepository

logger = get_logger(__name__)


class ProviderService:
    """Service for provider-related business logic"""

    def __init__(self, provider_repo: ProviderRepository):
        self.provider_repo = provider_repo

    def list_all(self) -> list[Provider]:
        """List all providers"""
        return self.provider_repo.find_all()

    def get_by_id(self, provider_id: str) -> Provider:
        """Get provider by ID, raise 404 if not found"""
        provider = self.provider_repo.find_by_id(provider_id)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider with ID '{provider_id}' not found",
            )
        return provider

    def create(
        self,
        name: str,
        provider_type: ProviderType,
        base_url: str | None = None,
        api_key_env_var: str | None = None,
    ) -> Provider:
        """Create a new provider"""
        # Validation logic remains same...
        if provider_type == ProviderType.CUSTOM:
            if not api_key_env_var:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Custom providers must specify api_key_env_var",
                )

            if not re.match(r"^[A-Z][A-Z0-9_]*$", api_key_env_var):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Invalid api_key_env_var format. Must be uppercase with "
                        "underscores (e.g., MY_CUSTOM_API_KEY)"
                    ),
                )

            if not base_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Custom providers must specify base_url",
                )

        elif api_key_env_var:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot specify api_key_env_var for {provider_type.value} provider. "
                    f"This provider uses predefined environment variable"
                ),
            )

        # Check if provider with same name already exists
        existing = self.provider_repo.find_by_name(name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Provider with name '{name}' already exists",
            )

        provider = Provider(
            name=name,
            provider_type=provider_type,
            base_url=base_url,
            api_key_env_var=api_key_env_var,
        )

        created = self.provider_repo.create(provider)
        self.provider_repo.commit()

        # Log warning if API key not configured
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
    ) -> Provider:
        """Update provider"""
        provider = self.get_by_id(provider_id)

        # Validate api_key_env_var updates
        if api_key_env_var is not None:
            if provider.provider_type != ProviderType.CUSTOM:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Cannot update api_key_env_var for {provider.provider_type.value} "
                        f"provider. This provider uses predefined environment variable"
                    ),
                )

            if not re.match(r"^[A-Z][A-Z0-9_]*$", api_key_env_var):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Invalid api_key_env_var format. Must be uppercase with "
                        "underscores (e.g., MY_CUSTOM_API_KEY)"
                    ),
                )

        if name is not None:
            provider.name = name
        if base_url is not None:
            provider.base_url = base_url
        if api_key_env_var is not None:
            provider.api_key_env_var = api_key_env_var

        updated = self.provider_repo.update(provider)
        self.provider_repo.commit()
        return updated

    def update_flags(self, provider_id: str, enabled: bool) -> Provider:
        """Update provider enabled/disabled state"""
        provider = self.get_by_id(provider_id)
        provider.enabled = enabled
        updated = self.provider_repo.update(provider)
        self.provider_repo.commit()

        logger.info(
            "provider_flags_updated",
            provider_id=provider_id,
            enabled=enabled,
        )
        return updated

    def delete(self, provider_id: str) -> None:
        """
        Providers cannot be deleted to maintain referential integrity.
        Use update_flags to disable the provider instead.
        """
        raise NotImplementedError(
            "Providers cannot be deleted. Use update_flags to disable the provider instead."
        )
