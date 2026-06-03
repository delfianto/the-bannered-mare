"""Character ORM model."""

# Bidirectional ORM relationships form TYPE_CHECKING-only import cycles with no
# runtime import edge; the file-level cycle report would be a false positive here.
# pyright: reportImportCycles=false
from __future__ import annotations

from typing import TYPE_CHECKING, final

from sqlalchemy import Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.persistence.enums import Gender
from src.core.persistence.models._base import BaseModel, StringList

if TYPE_CHECKING:
    from src.core.persistence.models.chat import Chat
    from src.core.persistence.models.lore import Lorebook


@final
class Character(BaseModel):
    """Character card data for roleplay interactions (NPC that the LLM roleplays as)"""

    __tablename__ = "characters"

    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Display name of the character"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Brief description or tagline for the character"
    )
    personality: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Detailed description of the character's traits and behavior"
    )
    first_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Initial message the character sends when starting a new chat"
    )
    example_dialogues: Mapped[list[str] | None] = mapped_column(
        StringList, nullable=True, comment="List of example exchanges to guide roleplay style"
    )
    avatar: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Path to the original avatar image file"
    )
    avatar_thumbnail: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Path to the generated avatar thumbnail image"
    )
    scenario: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Current scenario/situation for RP context"
    )
    post_history_instructions: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Jailbreak/instructions inserted after chat history"
    )
    alternate_greetings: Mapped[list[str] | None] = mapped_column(
        StringList, nullable=True, comment="Alternative first messages"
    )
    tags: Mapped[list[str] | None] = mapped_column(
        StringList, nullable=True, comment="Tags for categorizing and filtering characters"
    )
    gender: Mapped[Gender | None] = mapped_column(
        Enum(Gender, values_callable=lambda obj: [e.value for e in obj]),
        nullable=True,
        comment="Character's gender",
    )
    custom_gender: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Custom gender value when gender is set to 'others'"
    )
    creator: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Creator or author of the character card"
    )
    system_prompt: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Per-character system prompt override (V2 spec)"
    )
    creator_notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Creator's notes about the character (not sent to LLM)"
    )
    character_version: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Semantic version string from card spec"
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1", comment="Character card version"
    )

    chats: Mapped[list[Chat]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )
    lorebooks: Mapped[list[Lorebook]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )
