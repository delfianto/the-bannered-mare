"""Pydantic schemas for Model API validation"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.model_family.schemas import ModelFamilyResponse


class ModelBase(BaseModel):
    """Base model schema with common fields"""

    provider_id: str = Field(..., min_length=1, max_length=12, description="Provider ID")
    model_identifier: str = Field(
        ..., min_length=1, max_length=100, description="Actual API model name"
    )
    openrouter_identifier: str | None = Field(
        None, max_length=100, description="OpenRouter model name"
    )
    use_openrouter: bool = Field(False, description="Whether to route through OpenRouter")
    name: str = Field(..., min_length=1, max_length=100, description="User-friendly display name")
    model_family_id: str = Field(
        ..., min_length=1, max_length=12, description="Link to model family"
    )
    template_id: str | None = Field(None, max_length=12, description="Default prompt template")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="All model parameters (temperature, max_tokens, etc.)",
    )
    enabled: bool = Field(True, description="Whether model is available")


class ModelFilterParams(BaseModel):
    """Query parameters for filtering models"""

    name__ilike: str | None = Field(None, description="Search by name (case-insensitive)")
    provider_id: str | None = Field(None, description="Filter by provider")
    enabled: bool | None = Field(None, description="Filter by enabled status")

    def to_filter_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.model_dump().items() if v is not None}


class ModelCreate(ModelBase):
    """Schema for creating a new model definition"""

    pass


class ModelUpdate(BaseModel):
    """Schema for updating a model definition"""

    provider_id: str | None = Field(None, min_length=1, max_length=12)
    model_identifier: str | None = Field(None, min_length=1, max_length=100)
    openrouter_identifier: str | None = Field(None, max_length=100)
    use_openrouter: bool | None = None
    name: str | None = Field(None, min_length=1, max_length=100)
    model_family_id: str | None = Field(None, min_length=1, max_length=12)
    template_id: str | None = Field(None, max_length=12)
    parameters: dict[str, Any] | None = None
    enabled: bool | None = None


class ModelFlagsUpdate(BaseModel):
    """Schema for updating model flags only"""

    enabled: bool | None = None
    use_openrouter: bool | None = None


class ModelListResponse(BaseModel):
    """Schema for model list responses (excludes heavy fields)"""

    id: str
    provider_id: str
    model_identifier: str
    openrouter_identifier: str | None
    use_openrouter: bool
    name: str
    model_family_id: str
    enabled: bool
    created_at: datetime
    updated_at: datetime

    # Computed fields
    can_use_openrouter: bool
    active_identifier: str
    provider_enabled: bool

    model_config = ConfigDict(from_attributes=True)


class ModelResponse(ModelBase):
    """Schema for detailed model responses"""

    id: str
    created_at: datetime
    updated_at: datetime

    # Computed fields
    can_use_openrouter: bool
    active_identifier: str
    provider_enabled: bool

    model_config = ConfigDict(from_attributes=True)


class ModelDetailResponse(ModelResponse):
    """Schema for detailed model responses (includes embedded relationships)"""

    model_family: ModelFamilyResponse
