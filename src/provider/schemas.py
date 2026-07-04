"""Pydantic schemas for Provider API validation"""

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.provider.models import ProviderType


class DiscoveredModel(BaseModel):
    """A model discovered by querying a local provider's native API."""

    identifier: str = Field(description="Provider-native model identifier")
    display_name: str
    state: Literal["loaded", "not-loaded"]
    size_bytes: int | None = None
    quantization: str | None = None
    max_context_length: int | None = None


class AvailableModelsResponse(BaseModel):
    """Result of listing (or syncing) a provider's live model list."""

    provider_id: str
    models: list[DiscoveredModel]
    last_synced_at: datetime | None
    from_cache: bool


class ModelActionRequest(BaseModel):
    """Identifies which discovered model a load/unload action applies to."""

    model_identifier: str


class ModelActionResponse(BaseModel):
    """Result of a load/unload action."""

    model_identifier: str
    action: Literal["loaded", "unloaded"]


class ProviderCreate(BaseModel):
    """Schema for creating a new provider"""

    name: str = Field(..., max_length=100, description="Unique provider name")
    provider_type: ProviderType = Field(..., description="Type of provider")
    base_url: str | None = Field(
        default=None,
        max_length=255,
        description="API endpoint URL (optional, uses default for known providers)",
    )
    api_key_env_var: str | None = Field(
        default=None,
        max_length=100,
        description="Environment variable name for API key (required for CUSTOM providers)",
    )

    @field_validator("api_key_env_var")
    @classmethod
    def validate_api_key_env_var(cls, v: str | None):
        """Validate env var name format"""
        if v is not None and not re.match(r"^[A-Z][A-Z0-9_]*$", v):
            raise ValueError(
                "api_key_env_var must be uppercase with underscores (e.g., MY_CUSTOM_API_KEY)"
            )
        return v


class ProviderUpdate(BaseModel):
    """Schema for updating a provider"""

    name: str | None = Field(default=None, max_length=100)
    base_url: str | None = Field(default=None, max_length=255)
    api_key_env_var: str | None = Field(
        default=None,
        max_length=100,
        description="Environment variable name for API key (CUSTOM providers only)",
    )
    enabled: bool | None = None

    @field_validator("api_key_env_var")
    @classmethod
    def validate_api_key_env_var(cls, v: str | None):
        """Validate env var name format"""
        if v is not None and not re.match(r"^[A-Z][A-Z0-9_]*$", v):
            raise ValueError(
                "api_key_env_var must be uppercase with underscores (e.g., MY_CUSTOM_API_KEY)"
            )
        return v


class ProviderFlagsUpdate(BaseModel):
    """Schema for updating provider flags only"""

    enabled: bool


class ProviderResponse(BaseModel):
    """Schema for provider responses"""

    id: str
    name: str
    provider_type: str
    base_url: str | None
    enabled: bool
    created_at: datetime
    updated_at: datetime
    last_synced_at: datetime | None = None

    # Runtime status fields
    api_key_configured: bool = Field(description="Whether API key is available in environment")
    env_var_name: str | None = Field(description="Expected environment variable name for API key")

    model_config = ConfigDict(from_attributes=True)
