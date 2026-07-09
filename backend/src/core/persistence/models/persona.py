"""Persona ORM model."""

# Bidirectional ORM relationships form TYPE_CHECKING-only import cycles with no
# runtime import edge; the file-level cycle report would be a false positive here.
# pyright: reportImportCycles=false
from __future__ import annotations

from typing import TYPE_CHECKING, final

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.persistence.models._base import BaseModel

if TYPE_CHECKING:
    from src.core.persistence.models.chat import Chat


@final
class Persona(BaseModel):
    """User persona definitions"""

    __tablename__ = "personas"

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique name of the user persona",
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Detailed description of the user's role or characteristics"
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this persona is automatically selected for new chats",
    )
    avatar: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Path to the user persona avatar image"
    )
    avatar_large: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Path to the large (<=512px) full-portrait avatar"
    )
    avatar_thumbnail: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Path to the square head-crop avatar thumbnail"
    )

    chats: Mapped[list[Chat]] = relationship(back_populates="persona")
