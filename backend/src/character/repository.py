"""Data access layer for Character entities"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.character.models import Character
from src.core.persistence import BaseRepository


class CharacterRepository(BaseRepository[Character]):
    """Repository for Character data access with custom queries"""

    def __init__(self, db: Session):
        """Initialize Character repository"""
        super().__init__(db, Character)

    def find_by_name(self, name: str) -> Character | None:
        """Find a character by name"""
        stmt = select(Character).where(Character.name == name)
        return self.db.execute(stmt).scalars().first()

    def find_all_ordered(self) -> list[Character]:
        """Find all characters ordered by creation date"""
        stmt = select(Character).order_by(Character.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def find_paginated_ordered(
        self, limit: int = 10, offset: int = 0, filters: dict[str, Any] | None = None
    ) -> tuple[list[Character], int]:
        """Find characters ordered by creation date with pagination and filtering"""
        if limit > self.MAX_LIMIT:
            raise ValueError(f"Limit cannot exceed {self.MAX_LIMIT}")

        stmt = select(Character)
        stmt = self._apply_filters(stmt, filters)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()

        stmt = stmt.order_by(Character.created_at.desc()).limit(limit).offset(offset)
        items = list(self.db.execute(stmt).scalars().all())

        return items, total
