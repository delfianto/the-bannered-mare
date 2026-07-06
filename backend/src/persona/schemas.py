"""Pydantic schemas for Persona API"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class PersonaBase(BaseModel):
    """Base persona schema"""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(
        default=None, max_length=50000, description="Persona description for RP context"
    )
    avatar: str | None = Field(default=None, max_length=255)
    avatar_thumbnail: str | None = Field(default=None, max_length=255)
    is_default: bool = Field(False, description="Set as default persona")


class PersonaFilterParams(BaseModel):
    """Query parameters for filtering personas"""

    name__ilike: str | None = Field(default=None, description="Search persona name")
    is_default: bool | None = Field(default=None, description="Filter by default status")

    def to_filter_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.model_dump().items() if v is not None}


class PersonaCreate(PersonaBase):
    """Schema for creating a persona"""

    pass


class PersonaUpdate(BaseModel):
    """Schema for updating a persona"""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=50000)
    avatar: str | None = Field(default=None, max_length=255)
    is_default: bool | None = None


class PersonaResponse(PersonaBase):
    """Schema for persona response"""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("avatar")
    def serialize_avatar(self, avatar: str | None) -> str | None:
        if avatar and not (
            avatar.startswith("http://") or avatar.startswith("https://") or avatar.startswith("/")
        ):
            return f"/api/personas/{self.id}/avatar"
        return avatar

    @field_serializer("avatar_thumbnail")
    def serialize_avatar_thumbnail(self, avatar_thumbnail: str | None) -> str | None:
        if avatar_thumbnail and not (
            avatar_thumbnail.startswith("http://")
            or avatar_thumbnail.startswith("https://")
            or avatar_thumbnail.startswith("/")
        ):
            return f"/api/personas/{self.id}/avatar_thumbnail"
        return avatar_thumbnail
