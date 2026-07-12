"""Data access layer for Persona entities"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.persistence import BaseRepository
from src.persona.models import Persona


class PersonaRepository(BaseRepository[Persona]):
    """Repository for Persona data access with custom queries"""

    def __init__(self, db: Session):
        """Initialize Persona repository"""
        super().__init__(db, Persona)

    def find_all_ordered(self) -> list[Persona]:
        """Find all personas ordered by creation date"""
        stmt = select(Persona).order_by(Persona.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def find_paginated_ordered(
        self, limit: int = 10, offset: int = 0, filters: dict[str, Any] | None = None
    ) -> tuple[list[Persona], int]:
        """Find personas ordered by creation date with pagination and filtering"""
        if limit > self.MAX_LIMIT:
            raise ValueError(f"Limit cannot exceed {self.MAX_LIMIT}")

        stmt = select(Persona)
        stmt = self._apply_filters(stmt, filters)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()

        stmt = stmt.order_by(Persona.created_at.desc()).limit(limit).offset(offset)
        items = list(self.db.execute(stmt).scalars().all())

        return items, total

    def unset_all_defaults(self, exclude_id: str | None = None) -> None:
        """Unset all default personas, optionally excluding one by ID"""
        stmt = select(Persona).where(Persona.is_default)
        if exclude_id:
            stmt = stmt.where(Persona.id != exclude_id)

        result = self.db.execute(stmt).scalars().all()
        for persona in result:
            persona.is_default = False
        self.db.flush()
