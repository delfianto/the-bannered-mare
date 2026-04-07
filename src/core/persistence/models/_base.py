"""Shared types and utilities for ORM models."""

from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.dialects import postgresql

from src.core.persistence.base_model import BaseModel

# Use JSON for SQLite (tests) and ARRAY for Postgres (prod)
StringList = JSON().with_variant(postgresql.ARRAY(String), "postgresql")

__all__ = ["BaseModel", "StringList"]
