"""Pydantic schemas for Chat API validation"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChatBase(BaseModel):
    """Base chat schema with common fields"""

    character_id: str = Field(..., max_length=12, description="Character ID")
    model_id: str | None = Field(None, max_length=12, description="Model ID")
    title: str | None = Field(None, max_length=200, description="Chat title")


class ChatSessionFilterParams(BaseModel):
    """Query parameters for filtering chat sessions"""

    character_id: str | None = Field(None, description="Filter by character")
    model_id: str | None = Field(None, description="Filter by model")
    created_at__ge: datetime | None = Field(None, description="Sessions started after")
    created_at__le: datetime | None = Field(None, description="Sessions started before")

    def to_filter_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.model_dump().items() if v is not None}


class ChatCreate(ChatBase):
    """Schema for creating a new chat"""

    pass


class ChatUpdate(BaseModel):
    """Schema for updating a chat"""

    title: str | None = Field(None, max_length=200)
    model_id: str | None = Field(None, max_length=12)
    preset_id: str | None = Field(None, max_length=12)


class ChatCharacterResponse(BaseModel):
    """Nested character info in chat response"""

    id: str
    name: str
    avatar: str | None = None
    avatar_thumbnail: str | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


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
    created_at: datetime
    updated_at: datetime

    character: ChatCharacterResponse
    model: ChatModelResponse

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
            "created_at": data.created_at,
            "updated_at": data.updated_at,
            "character": data.character,
            "model": {
                "id": data.model_id,
                "name": data.model_name,
            },
        }
