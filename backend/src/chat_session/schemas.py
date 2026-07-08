"""Pydantic schemas for Chat API validation"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator


class ChatBase(BaseModel):
    """Base chat schema with common fields"""

    character_id: str = Field(..., max_length=12, description="Character ID")
    model_id: str | None = Field(default=None, max_length=12, description="Model ID")
    title: str | None = Field(default=None, max_length=200, description="Chat title")
    profile_id: str | None = Field(
        default=None, max_length=12, description="Profile to apply on creation"
    )
    is_bookmarked: bool = Field(default=False, description="Whether the chat session is bookmarked")


class ChatSessionFilterParams(BaseModel):
    """Query parameters for filtering chat sessions"""

    character_id: str | None = Field(default=None, description="Filter by character")
    model_id: str | None = Field(default=None, description="Filter by model")
    created_at__ge: datetime | None = Field(default=None, description="Sessions started after")
    created_at__le: datetime | None = Field(default=None, description="Sessions started before")

    def to_filter_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.model_dump().items() if v is not None}


class ChatCreate(ChatBase):
    """Schema for creating a new chat"""

    pass


class ChatUpdate(BaseModel):
    """Schema for updating a chat"""

    title: str | None = Field(default=None, max_length=200)
    model_id: str | None = Field(default=None, max_length=12)
    preset_id: str | None = Field(default=None, max_length=12)
    is_bookmarked: bool | None = Field(default=None)


class ChatApplyProfile(BaseModel):
    """Body for applying a profile (loadout) to an existing chat"""

    profile_id: str = Field(..., max_length=12, description="Profile to apply")


class ChatCharacterResponse(BaseModel):
    """Nested character info in chat response"""

    id: str
    name: str
    avatar: str | None = None
    avatar_thumbnail: str | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_serializer("avatar")
    def serialize_avatar(self, avatar: str | None) -> str | None:
        if avatar and not (
            avatar.startswith("http://") or avatar.startswith("https://") or avatar.startswith("/")
        ):
            return f"/api/characters/{self.id}/avatar"
        return avatar

    @field_serializer("avatar_thumbnail")
    def serialize_avatar_thumbnail(self, avatar_thumbnail: str | None) -> str | None:
        if avatar_thumbnail and not (
            avatar_thumbnail.startswith("http://")
            or avatar_thumbnail.startswith("https://")
            or avatar_thumbnail.startswith("/")
        ):
            return f"/api/characters/{self.id}/avatar_thumbnail"
        return avatar_thumbnail


class ChatModelResponse(BaseModel):
    """Nested model info in chat response"""

    id: str | None
    name: str | None

    model_config = ConfigDict(from_attributes=True)


class ChatResponse(BaseModel):
    """Schema for chat responses"""

    id: str
    title: str | None = None
    preview: str | None = None
    is_bookmarked: bool | None = None
    created_at: datetime
    updated_at: datetime

    character: ChatCharacterResponse
    model: ChatModelResponse

    template_id: str | None = None
    preset_id: str | None = None
    persona_id: str | None = None
    task_model_id: str | None = None
    initial_profile_name: str | None = None
    last_profile_name: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _map_nested_objects(cls, data: Any) -> Any:
        """Map flat fields or relationships to nested structure"""
        if isinstance(data, dict):
            if "character" not in data:
                data["character"] = {
                    "id": data.get("character_id"),
                    "name": data.get("character_name"),
                    "avatar": data.get("avatar"),
                    "avatar_thumbnail": data.get("avatar_thumbnail"),
                }
            if "model" not in data:
                data["model"] = {"id": data.get("model_id"), "name": data.get("model_name")}
            return data

        return {
            "id": data.id,
            "title": data.title,
            "preview": data.preview,
            "is_bookmarked": data.is_bookmarked,
            "created_at": data.created_at,
            "updated_at": data.updated_at,
            "character": data.character,
            "model": {
                "id": data.model_id,
                "name": data.model_name,
            },
            "template_id": data.template_id,
            "preset_id": data.preset_id,
            "persona_id": data.persona_id,
            "task_model_id": data.task_model_id,
            "initial_profile_name": data.initial_profile_name,
            "last_profile_name": data.last_profile_name,
        }
