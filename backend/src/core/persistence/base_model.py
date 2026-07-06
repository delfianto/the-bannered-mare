"""Base model with common fields for all entities"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.core.persistence.utils import gen_id


class Base(DeclarativeBase):
    """Declarative base for all models"""

    pass


def utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime"""
    return datetime.now(UTC)


class BaseModel(Base):
    """Abstract base model with common fields"""

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String(12),
        primary_key=True,
        default=gen_id,
        comment="Unique short identifier (12 characters)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        comment="Timestamp when the record was created (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
        comment="Timestamp when the record was last updated (UTC)",
    )
