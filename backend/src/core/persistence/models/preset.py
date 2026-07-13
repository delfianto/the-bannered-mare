"""Preset ORM model."""

# Bidirectional ORM relationships form TYPE_CHECKING-only import cycles with no
# runtime import edge; the file-level cycle report would be a false positive here.
# pyright: reportImportCycles=false
from __future__ import annotations

from typing import TYPE_CHECKING, Any, final

from sqlalchemy import Boolean, String, Text
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.persistence.models._base import BaseModel, mutable_json

if TYPE_CHECKING:
    from src.core.persistence.models.chat import Chat


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
        MutableDict.as_mutable(mutable_json()),
        default=dict,
        nullable=False,
        comment="Sampling parameter overrides (temperature, top_p, etc.)",
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Whether this preset is the default"
    )

    chats: Mapped[list[Chat]] = relationship(back_populates="preset")
