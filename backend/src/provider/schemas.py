"""Pydantic schemas for Provider API validation"""

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.provider.models import ProviderType

# A CUSTOM provider's api_key_env_var is resolved with os.getenv() and sent as a
# Bearer token to its base_url, so it must look like a *credential* variable and
# must never name one of the application's own secrets — otherwise a provider
# pointed at an attacker URL could exfiltrate them.
_ALLOWED_KEY_SUFFIXES = ("_API_KEY", "_KEY", "_TOKEN")
_FORBIDDEN_KEY_SUBSTRINGS = ("SECRET", "PASSWORD", "PRIVATE")
_FORBIDDEN_KEY_NAMES = frozenset({"ENCRYPTION_KEY", "DATABASE_URL"})


def _validate_api_key_env_var(v: str | None) -> str | None:
    """Restrict api_key_env_var to credential-shaped names, never app secrets."""
    if v is None:
        return v
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", v):
        raise ValueError("api_key_env_var must be uppercase letters, digits, and underscores")
    if (
        not v.endswith(_ALLOWED_KEY_SUFFIXES)
        or v in _FORBIDDEN_KEY_NAMES
        or any(s in v for s in _FORBIDDEN_KEY_SUBSTRINGS)
    ):
        raise ValueError(
            "api_key_env_var must name a provider credential variable "
            "(e.g. MYPROVIDER_API_KEY) and cannot reference an application secret"
        )
    return v


def _validate_base_url(v: str | None) -> str | None:
    """Require an http(s) scheme so the server can't be pointed at file://, etc."""
    if v is None:
        return v
    if not re.match(r"^https?://", v):
        raise ValueError("base_url must start with http:// or https://")
    return v


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


class ModelSearchResponse(BaseModel):
    """Substring matches for a model-name query against a provider's live list."""

    provider_id: str
    query: str
    models: list[DiscoveredModel]


class ProviderModelFilterUpdate(BaseModel):
    """Sets the curated allow-list that narrows a provider's available models."""

    allowed_models: list[str] = Field(
        default_factory=list,
        description="Provider-native model identifiers to keep; empty shows all",
    )


class ModelActionRequest(BaseModel):
    """Identifies which discovered model a load/unload action applies to."""

    model_identifier: str


class ModelActionResponse(BaseModel):
    """Result of a load/unload action."""

    model_identifier: str
    action: Literal["loaded", "unloaded", "deleted"]


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

    _check_base_url = field_validator("base_url")(_validate_base_url)
    _check_api_key_env_var = field_validator("api_key_env_var")(_validate_api_key_env_var)


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

    _check_base_url = field_validator("base_url")(_validate_base_url)
    _check_api_key_env_var = field_validator("api_key_env_var")(_validate_api_key_env_var)

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
    allowed_models: list[str] = Field(
        default_factory=list,
        description="Curated allow-list of model identifiers; empty means all are shown",
    )

    # Runtime status fields
    api_key_configured: bool = Field(description="Whether API key is available in environment")
    env_var_name: str | None = Field(description="Expected environment variable name for API key")

    # Static naming metadata (derived from provider type). A model's identifier
    # scheme depends on its provider — the provider is the route.
    identifier_style: str = Field(
        description="Short label for this provider's model-identifier scheme (e.g. vendor/model)"
    )
    identifier_hint: str = Field(
        description="Human-friendly explanation of the identifier scheme, with an example"
    )

    model_config = ConfigDict(from_attributes=True)
