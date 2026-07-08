"""Profile ORM model."""

from __future__ import annotations

from typing import final

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.persistence.models._base import BaseModel


@final
class Profile(BaseModel):
    """Named bundle of session settings (prompt template, sampler preset, persona, model).

    The SillyTavern equivalent of a "preset": a single selectable unit that, when
    applied to a chat, sets each referenced axis. References are FK-only and nullable
    (``ON DELETE SET NULL``) so a profile that loses one axis falls back rather than
    becoming invalid.
    """

    __tablename__ = "profiles"

    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True, comment="Display name of the profile"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Brief description of the profile's purpose"
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this profile is the default",
    )
    prompt_template_id: Mapped[str | None] = mapped_column(
        String(12),
        ForeignKey("prompt_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Prompt template applied to chats using this profile",
    )
    preset_id: Mapped[str | None] = mapped_column(
        String(12),
        ForeignKey("presets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Sampler preset applied to chats using this profile",
    )
    persona_id: Mapped[str | None] = mapped_column(
        String(12),
        ForeignKey("personas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Default persona applied to chats using this profile",
    )
    model_id: Mapped[str | None] = mapped_column(
        String(12),
        ForeignKey("models.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Default model applied to chats using this profile",
    )
    task_model_id: Mapped[str | None] = mapped_column(
        String(12),
        ForeignKey("models.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional cheaper model for auxiliary calls (titles, suggestions); "
        "falls back to the chat model when unset",
    )
    source: Mapped[str] = mapped_column(
        String(20),
        default="manual",
        nullable=False,
        comment="Origin of the profile: manual, sillytavern, etc.",
    )
    source_filename: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Original filename when imported (preserves an imported preset's identity)",
    )
