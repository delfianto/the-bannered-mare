"""Preset ORM model."""

from __future__ import annotations

from typing import Any, final

from sqlalchemy import JSON, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.persistence.models._base import BaseModel


@final
class Preset(BaseModel):
    """Named parameter preset for LLM generation settings"""

    __tablename__ = "presets"

    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True, comment="Display name of the preset"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Brief description of the preset's purpose"
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        comment="Sampling parameter overrides (temperature, top_p, etc.)",
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Whether this preset is the default"
    )

    chats: Mapped[list[Chat]] = relationship(back_populates="preset")
