"""Pydantic schemas for Character API validation"""

from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from src.core.persistence.enums import Gender
from src.core.schemas import AvatarUrlMixin, BaseFilterParams


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


class CharacterFilterParams(BaseFilterParams):
    """Query parameters for filtering characters"""

    name__ilike: str | None = Field(default=None, description="Search name")
    gender: Gender | None = Field(default=None, description="Filter by gender")
    tags__ilike: str | None = Field(default=None, description="Filter by tag content")
    created_at__ge: datetime | None = Field(default=None, description="Created after date")


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


class CharacterFormBase(BaseModel):
    """Multipart create/update payload, declared once and consumed by both the
    router and the service so the ~17-field character payload is no longer spelled
    out four times.

    Distinct from ``CharacterCreate``/``CharacterUpdate``: over multipart the list
    fields arrive as JSON *strings* (the service parses them) and every field is
    optional so the same shape serves a partial update. Deliberately carries **no**
    ``UploadFile`` — the avatar rides on the router-only ``CharacterFormPayload``
    (see router.py), keeping FastAPI transport types out of the service layer.
    """

    name: str | None = None
    description: str | None = None
    personality: str | None = None
    first_message: str | None = None
    example_dialogues: str | None = None  # JSON string
    scenario: str | None = None
    post_history_instructions: str | None = None
    alternate_greetings: str | None = None  # JSON string
    tags: str | None = None  # JSON string
    gender: str | None = None
    custom_gender: str | None = None
    creator: str | None = None
    version: int | None = None
    system_prompt: str | None = None
    creator_notes: str | None = None
    species: str | None = None
    age: str | None = None


class CharacterResponse(CharacterBase, AvatarUrlMixin):
    """Schema for character responses"""

    avatar_resource: ClassVar[str] = "characters"

    id: str
    avatar: str | None
    avatar_large: str | None
    avatar_thumbnail: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
