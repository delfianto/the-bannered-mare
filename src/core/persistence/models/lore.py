"""Lorebook and LoreEntry ORM models."""

from __future__ import annotations

from typing import final

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.persistence.enums import InsertionPosition, MessageRole, SecondaryLogic
from src.core.persistence.models._base import BaseModel, StringList


@final
class Lorebook(BaseModel):
    """Collection of lore entries attached to a character or global"""

    __tablename__ = "lorebooks"

    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="Display name")
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Optional description"
    )
    is_global: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Applies to all chats globally"
    )
    character_id: Mapped[str | None] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=True, comment="Owning character"
    )

    character: Mapped[Character | None] = relationship(back_populates="lorebooks")
    entries: Mapped[list[LoreEntry]] = relationship(
        back_populates="lorebook", cascade="all, delete-orphan", order_by="LoreEntry.order"
    )


@final
class LoreEntry(BaseModel):
    """Single piece of world knowledge with activation keywords"""

    __tablename__ = "lore_entries"

    lorebook_id: Mapped[str] = mapped_column(
        ForeignKey("lorebooks.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="Display name / memo")
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Lore text injected into prompt"
    )

    keys: Mapped[list[str]] = mapped_column(
        StringList, nullable=False, default=list, comment="Primary trigger keywords"
    )
    secondary_keys: Mapped[list[str]] = mapped_column(
        StringList, nullable=False, default=list, comment="Secondary filter keywords"
    )
    secondary_logic: Mapped[SecondaryLogic] = mapped_column(
        Enum(SecondaryLogic, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=SecondaryLogic.AND_ANY,
        comment="Logic for secondary keyword matching",
    )

    case_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    match_whole_words: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    use_regex: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    constant: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Always active, ignores keywords"
    )

    position: Mapped[InsertionPosition] = mapped_column(
        Enum(InsertionPosition, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=InsertionPosition.AFTER_CHARACTER,
    )
    depth: Mapped[int] = mapped_column(
        Integer, default=4, nullable=False, comment="Message depth for AT_DEPTH position"
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=MessageRole.SYSTEM,
        comment="Message role for AT_DEPTH insertion",
    )
    priority: Mapped[int] = mapped_column(
        Integer, default=100, nullable=False, comment="Higher = inserted first"
    )

    scan_depth: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Per-entry scan depth override"
    )
    ignore_budget: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    lorebook: Mapped[Lorebook] = relationship(back_populates="entries")
