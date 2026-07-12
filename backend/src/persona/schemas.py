"""Pydantic schemas for Persona API"""

from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from src.core.schemas import AvatarUrlMixin, BaseFilterParams


class PersonaBase(BaseModel):
    """Base persona schema"""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(
        default=None, max_length=50000, description="Persona description for RP context"
    )
    avatar: str | None = Field(default=None, max_length=255)
    avatar_large: str | None = Field(default=None, max_length=255)
    avatar_thumbnail: str | None = Field(default=None, max_length=255)
    is_default: bool = Field(False, description="Set as default persona")


class PersonaFilterParams(BaseFilterParams):
    """Query parameters for filtering personas"""

    name__ilike: str | None = Field(default=None, description="Search persona name")
    is_default: bool | None = Field(default=None, description="Filter by default status")


class PersonaCreate(PersonaBase):
    """Schema for creating a persona"""

    pass


class PersonaUpdate(BaseModel):
    """Schema for updating a persona"""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=50000)
    avatar: str | None = Field(default=None, max_length=255)
    is_default: bool | None = None


class PersonaResponse(PersonaBase, AvatarUrlMixin):
    """Schema for persona response"""

    avatar_resource: ClassVar[str] = "personas"

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
