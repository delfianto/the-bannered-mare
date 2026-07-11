"""Pydantic schemas for canonical models (registry) + provider routes."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.model_family.schemas import ModelFamilyResponse


# ── Routes ───────────────────────────────────────────────────
class ModelRouteBase(BaseModel):
    """A provider binding: the provider + the identifier that provider uses."""

    provider_id: str = Field(..., min_length=1, max_length=12, description="Provider ID")
    model_identifier: str = Field(
        ..., min_length=1, max_length=100, description="Provider-specific model identifier"
    )
    enabled: bool = Field(True, description="Whether this route is usable")


class ModelRouteCreate(ModelRouteBase):
    """Schema for adding a route to a canonical model."""

    pass


class ModelRouteResponse(ModelRouteBase):
    """Schema for a route in responses."""

    id: str
    model_registry_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActiveRouteUpdate(BaseModel):
    """Schema for flipping which route a canonical model resolves to."""

    route_id: str = Field(..., min_length=1, max_length=12, description="Route to make active")


# ── Registry (the user-facing "model") ───────────────────────
class ModelBase(BaseModel):
    """Base canonical-model schema."""

    slug: str | None = Field(
        default=None,
        max_length=100,
        description="Provider-independent identity; derived from the first route if omitted",
    )
    display_name: str = Field(
        ..., min_length=1, max_length=100, description="User-friendly display name"
    )
    original_identifier: str | None = Field(
        default=None,
        max_length=100,
        description="Native/canonical identifier; derived from the first route if omitted",
    )
    model_family_id: str = Field(
        ..., min_length=1, max_length=12, description="Link to model family"
    )
    template_id: str | None = Field(
        default=None, max_length=12, description="Default prompt template"
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Per-model parameter overrides"
    )
    enabled: bool = Field(True, description="Whether the model is available")


class ModelFilterParams(BaseModel):
    """Query parameters for filtering canonical models."""

    name__ilike: str | None = Field(default=None, description="Search by display name")
    provider_id: str | None = Field(default=None, description="Has a route on this provider")
    model_family_id: str | None = Field(default=None, description="Filter by model family")
    enabled: bool | None = Field(default=None, description="Filter by enabled status")

    def to_filter_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.model_dump().items() if v is not None}


class ModelCreate(ModelBase):
    """Schema for creating a canonical model with its initial route(s)."""

    routes: list[ModelRouteCreate] = Field(
        default_factory=list, description="Initial provider routes (first becomes active)"
    )
    active_provider_id: str | None = Field(
        default=None, description="Which route's provider is active; defaults to the first route"
    )


class ModelUpdate(BaseModel):
    """Schema for updating canonical-model fields (not its routes)."""

    slug: str | None = Field(default=None, min_length=1, max_length=100)
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    original_identifier: str | None = Field(default=None, min_length=1, max_length=100)
    model_family_id: str | None = Field(default=None, min_length=1, max_length=12)
    template_id: str | None = Field(default=None, max_length=12)
    parameters: dict[str, Any] | None = None
    enabled: bool | None = None


class ModelFlagsUpdate(BaseModel):
    """Schema for updating canonical-model flags only."""

    enabled: bool | None = None


class ModelListResponse(BaseModel):
    """Schema for canonical-model list responses (embeds routes for the UI)."""

    id: str
    slug: str
    display_name: str
    original_identifier: str
    model_family_id: str
    enabled: bool
    active_route_id: str | None
    routes: list[ModelRouteResponse]
    created_at: datetime
    updated_at: datetime

    # Computed: reachable only if the active route + its provider are enabled.
    provider_enabled: bool

    model_config = ConfigDict(from_attributes=True)


class ModelResponse(ModelBase):
    """Schema for a canonical model (with routes)."""

    id: str
    active_route_id: str | None
    routes: list[ModelRouteResponse]
    created_at: datetime
    updated_at: datetime

    provider_enabled: bool

    model_config = ConfigDict(from_attributes=True)


class ModelDetailResponse(ModelResponse):
    """Canonical model with the embedded family."""

    model_family: ModelFamilyResponse
