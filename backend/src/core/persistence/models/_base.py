"""Shared types and utilities for ORM models."""

from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.dialects import postgresql

from src.core.persistence.base_model import BaseModel

# Use JSON for SQLite (tests) and ARRAY for Postgres (prod)
StringList = JSON().with_variant(postgresql.ARRAY(String), "postgresql")

# Use JSON for SQLite (tests) and JSONB for Postgres (prod)
JsonDict = JSON().with_variant(postgresql.JSONB, "postgresql")


def mutable_json() -> JSON:
    """A fresh JSON/JSONB type instance for a ``Mutable``-tracked column.

    Each ``MutableDict`` / ``MutableList`` column must wrap its OWN type instance:
    reusing one shared instance makes the mutable associations collide (e.g. a
    list column gets coerced by the dict tracker and rejects lists), so this
    returns a new instance per call.
    """
    return JSON().with_variant(postgresql.JSONB, "postgresql")


__all__ = ["BaseModel", "StringList", "JsonDict", "mutable_json"]
