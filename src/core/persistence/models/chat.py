"""Chat, Message, and MessageAlternative ORM models."""

# Bidirectional ORM relationships form TYPE_CHECKING-only import cycles with no
# runtime import edge; the file-level cycle report would be a false positive here.
# pyright: reportImportCycles=false
from __future__ import annotations

from typing import TYPE_CHECKING, final

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.persistence.enums import MessageRole
from src.core.persistence.models._base import BaseModel

if TYPE_CHECKING:
    from src.core.persistence.models.character import Character
    from src.core.persistence.models.model import Model
    from src.core.persistence.models.persona import Persona
    from src.core.persistence.models.preset import Preset
    from src.core.persistence.models.prompt import PromptTemplate


@final
class Message(BaseModel):
    """Individual message within a chat conversation"""

    __tablename__ = "messages"

    chat_id: Mapped[str] = mapped_column(
        String(12),
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Unique identifier of the chat this message belongs to",
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        comment="Role of the message sender (user, assistant, system)",
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Full text content of the message"
    )
    token_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Cached token count for this message"
    )
    reasoning_content: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Reasoning/thinking content from the model"
    )
    active_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Index of the currently active alternative (0 = original)",
    )

    chat: Mapped[Chat] = relationship(back_populates="messages")
    alternatives: Mapped[list[MessageAlternative]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="MessageAlternative.ordinal",
    )


@final
class MessageAlternative(BaseModel):
    """Alternative response for a message (swipe)"""

    __tablename__ = "message_alternatives"

    message_id: Mapped[str] = mapped_column(
        String(12),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent message this alternative belongs to",
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="Alternative response text")
    token_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Cached token count"
    )
    ordinal: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Position in the alternatives list (0-based)"
    )

    message: Mapped[Message] = relationship(back_populates="alternatives")


@final
class Chat(BaseModel):
    """Conversation session between user and character using a specific model"""

    __tablename__ = "chats"

    character_id: Mapped[str] = mapped_column(
        String(12),
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Unique identifier of the character being roleplayed",
    )
    model_id: Mapped[str | None] = mapped_column(
        String(12),
        ForeignKey("models.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Unique identifier of the LLM model used for this chat",
    )
    title: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="User-defined or auto-generated title for the conversation",
    )
    preview: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Short text snippet of the last message for list display",
    )
    model_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Snapshot of the model name used (persists even if model is deleted)",
    )
    template_id: Mapped[str | None] = mapped_column(
        String(12),
        ForeignKey("prompt_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Prompt template (uses default if None)",
    )
    persona_id: Mapped[str | None] = mapped_column(
        String(12),
        ForeignKey("personas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User persona (uses default if None)",
    )
    preset_id: Mapped[str | None] = mapped_column(
        String(12),
        ForeignKey("presets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Parameter preset (uses model defaults if None)",
    )
    initial_profile_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Name of the profile this chat was created with (provenance snapshot, immutable)",
    )
    last_profile_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Name of the most recently applied profile (provenance snapshot, not an FK)",
    )

    character: Mapped[Character] = relationship(back_populates="chats")
    model: Mapped[Model | None] = relationship(back_populates="chats")
    template: Mapped[PromptTemplate | None] = relationship(back_populates="chats")
    persona: Mapped[Persona | None] = relationship(back_populates="chats")
    preset: Mapped[Preset | None] = relationship(back_populates="chats")
    messages: Mapped[list[Message]] = relationship(
        back_populates="chat", cascade="all, delete-orphan"
    )
