"""Pydantic schemas for ModelFamily API validation"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelFamilyBase(BaseModel):
    """Base model family schema with common fields"""

    name: str = Field(..., max_length=100, description="Unique model family name")
    family_identifier: str = Field(
        ..., max_length=100, description="URL-safe identifier following provider/model-name pattern"
    )
    description: str | None = Field(default=None, description="Description of the model family")
    provider_types: list[str] = Field(
        default_factory=list,
        description="List of provider types this family belongs to",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Per-parameter configuration: type, default, ranges, etc.",
    )
    unsupported_parameters: list[str] = Field(
        default_factory=list,
        description="List of parameters explicitly known to be unsupported",
    )
    extra_metadata: dict[str, Any] | None = Field(
        default=None, description="Additional metadata about the model family"
    )


class ModelFamilyFilterParams(BaseModel):
    """Query parameters for filtering model families"""

    name__ilike: str | None = Field(default=None, description="Search family name")
    family_identifier: str | None = Field(default=None, description="Exact match identifier")

    def to_filter_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.model_dump().items() if v is not None}


class ModelFamilyCreate(ModelFamilyBase):
    """Schema for creating a new model family"""

    pass


class ModelFamilyUpdate(BaseModel):
    """Schema for updating a model family"""

    name: str | None = Field(default=None, max_length=100)
    family_identifier: str | None = Field(default=None, max_length=100)
    description: str | None = None
    provider_types: list[str] | None = None
    parameters: dict[str, Any] | None = None
    unsupported_parameters: list[str] | None = None
    extra_metadata: dict[str, Any] | None = None


class ModelFamilyListResponse(BaseModel):
    """Schema for model family list responses (excludes heavy fields)"""

    id: str
    name: str
    family_identifier: str
    description: str | None
    provider_types: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModelFamilyResponse(ModelFamilyBase):
    """Schema for detailed model family responses"""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
