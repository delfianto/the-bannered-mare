"""Pydantic schemas for Character API validation"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from src.core.persistence.enums import Gender


class CharacterBase(BaseModel):
    """Base character schema with common fields"""

    name: str = Field(..., min_length=1, max_length=100, description="Character name")
    description: str | None = Field(
        default=None, max_length=50000, description="Character description"
    )
    personality: str | None = Field(
        default=None, max_length=50000, description="Personality traits and behavior"
    )
    first_message: str | None = Field(
        default=None, max_length=50000, description="Initial greeting message"
    )
    example_dialogues: list[str] | None = Field(
        default=None, description="List of example dialogue strings"
    )
    scenario: str | None = Field(
        default=None, max_length=50000, description="Current scenario context"
    )
    post_history_instructions: str | None = Field(
        default=None, max_length=50000, description="Instructions after history"
    )
    alternate_greetings: list[str] | None = Field(
        default=None, description="Alternative first messages"
    )

    # Character Card Format fields
    tags: list[str] | None = Field(default=None, description="Tags for categorization")
    gender: Gender | None = Field(default=None, description="Character gender")
    custom_gender: str | None = Field(
        default=None, max_length=100, description="Custom gender value when gender is 'others'"
    )
    creator: str | None = Field(
        default=None, max_length=100, description="Character creator/author"
    )
    species: str | None = Field(default=None, max_length=100, description="Character species")
    age: str | None = Field(default=None, max_length=100, description="Character age")
    system_prompt: str | None = Field(
        default=None, max_length=50000, description="Per-character system prompt override"
    )
    creator_notes: str | None = Field(
        default=None, max_length=50000, description="Creator's notes (not sent to LLM)"
    )
    character_version: str | None = Field(
        default=None, max_length=100, description="Semantic version from card spec"
    )
    version: int = Field(default=1, description="Character card version")


class CharacterFilterParams(BaseModel):
    """Query parameters for filtering characters"""

    name__ilike: str | None = Field(default=None, description="Search name")
    gender: Gender | None = Field(default=None, description="Filter by gender")
    tags__ilike: str | None = Field(default=None, description="Filter by tag content")
    created_at__ge: datetime | None = Field(default=None, description="Created after date")

    def to_filter_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.model_dump().items() if v is not None}


class CharacterCreate(CharacterBase):
    """Schema for creating a new character"""

    pass


class CharacterUpdate(BaseModel):
    """Schema for updating a character"""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=50000)
    personality: str | None = Field(default=None, max_length=50000)
    first_message: str | None = Field(default=None, max_length=50000)
    example_dialogues: list[str] | None = None
    scenario: str | None = Field(default=None, max_length=50000)
    post_history_instructions: str | None = Field(default=None, max_length=50000)
    alternate_greetings: list[str] | None = None

    # Character Card Format fields
    tags: list[str] | None = None
    gender: Gender | None = None
    custom_gender: str | None = Field(default=None, max_length=100)
    creator: str | None = Field(default=None, max_length=100)
    species: str | None = Field(default=None, max_length=100)
    age: str | None = Field(default=None, max_length=100)
    system_prompt: str | None = Field(default=None, max_length=50000)
    creator_notes: str | None = Field(default=None, max_length=50000)
    character_version: str | None = Field(default=None, max_length=100)
    version: int | None = None


class CharacterResponse(CharacterBase):
    """Schema for character responses"""

    id: str
    avatar: str | None
    avatar_large: str | None
    avatar_thumbnail: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("avatar")
    def serialize_avatar(self, avatar: str | None) -> str | None:
        if avatar and not (
            avatar.startswith("http://") or avatar.startswith("https://") or avatar.startswith("/")
        ):
            return f"/api/characters/{self.id}/avatar"
        return avatar

    @field_serializer("avatar_large")
    def serialize_avatar_large(self, avatar_large: str | None) -> str | None:
        if avatar_large and not (
            avatar_large.startswith("http://")
            or avatar_large.startswith("https://")
            or avatar_large.startswith("/")
        ):
            return f"/api/characters/{self.id}/avatar_large"
        return avatar_large

    @field_serializer("avatar_thumbnail")
    def serialize_avatar_thumbnail(self, avatar_thumbnail: str | None) -> str | None:
        if avatar_thumbnail and not (
            avatar_thumbnail.startswith("http://")
            or avatar_thumbnail.startswith("https://")
            or avatar_thumbnail.startswith("/")
        ):
            return f"/api/characters/{self.id}/avatar_thumbnail"
        return avatar_thumbnail
