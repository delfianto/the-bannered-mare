"""Pydantic schemas for Message API validation"""

from dataclasses import asdict, dataclass
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.chat_message.models import MessageRole
from src.core.schemas import PaginatedResponse


class MessageBase(BaseModel):
    """Base message schema with common fields"""

    role: MessageRole = Field(..., description="Message role (user/assistant/system)")
    content: str = Field(..., description="Message content")


class MessageCreate(BaseModel):
    """Schema for creating a new message (user message)"""

    content: str = Field(..., min_length=1, description="Message content")


class MessageUpdate(BaseModel):
    """Schema for editing a message"""

    content: str = Field(..., min_length=1, description="Updated message content")


class MessageResponse(MessageBase):
    """Schema for message responses"""

    id: str
    chat_id: str
    token_count: int | None = None
    reasoning_content: str | None = None
    active_index: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlternativeResponse(BaseModel):
    """Schema for a message alternative (swipe)"""

    id: str
    message_id: str
    content: str
    token_count: int | None = None
    ordinal: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Paginated response type alias
MessageListResponse = PaginatedResponse[MessageResponse]


@dataclass
class StreamEvent:
    """Typed SSE event emitted by the streaming pipeline."""

    type: str  # "start" | "text" | "reasoning" | "usage" | "done" | "error"
    content: str | None = None
    message_id: str | None = None
    finish_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    prompt_tokens: int | None = None
    cache_read_tokens: int | None = None
    cache_creation_tokens: int | None = None
    message: str | None = None
    code: str | None = None


def stream_event_to_dict(event: StreamEvent) -> dict:
    """Serialize a StreamEvent, omitting None fields for compact JSON."""
    return {k: v for k, v in asdict(event).items() if v is not None}
