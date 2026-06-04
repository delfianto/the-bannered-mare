"""RAG models: Embedding vectors and Data Bank entries."""

from __future__ import annotations

from typing import final

from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.persistence.models._base import BaseModel

# pgvector Vector type — imported at runtime only when PostgreSQL is used.
# For SQLite tests, the column is treated as a generic binary/text type.
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None  # type: ignore[assignment, misc]


@final
class Embedding(BaseModel):
    """Vector embedding for semantic search (chat messages + data bank entries)"""

    __tablename__ = "embeddings"

    source_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True, comment="Source: message, data_bank"
    )
    source_id: Mapped[str] = mapped_column(
        String(12), nullable=False, index=True, comment="ID of the source entity"
    )
    content_hash: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True, comment="Hash for dedup"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="Original text chunk")
    chunk_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Position within chunked source"
    )
    model_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Embedding model that produced this vector"
    )
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False, comment="Vector dimensions")

    # The vector column — defined conditionally based on pgvector availability.
    # Dimension is pinned (matches EmbeddingSettings.dimensions / nomic-embed-text)
    # because the VectorChord vchordrq index requires a fixed-dimension column.
    if Vector is not None:
        embedding = Column(Vector(768), nullable=False)


@final
class DataBankEntry(BaseModel):
    """User-managed knowledge entry for RAG retrieval"""

    __tablename__ = "data_bank_entries"

    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="Display name")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="Knowledge text")
    scope: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="global",
        index=True,
        comment="Scope: global, character, chat",
    )
    character_id: Mapped[str | None] = mapped_column(
        String(12),
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="For character-scoped entries",
    )
    chat_id: Mapped[str | None] = mapped_column(
        String(12),
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="For chat-scoped entries",
    )
