"""Data access layer for Preset entities"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.persistence import BaseRepository
from src.preset.models import Preset


class PresetRepository(BaseRepository[Preset]):
    """Repository for Preset data access with custom queries"""

    def __init__(self, db: Session):
        super().__init__(db, Preset)

    def find_default(self) -> Preset | None:
        """Find the default preset"""
        stmt = select(Preset).where(Preset.is_default)
        return self.db.execute(stmt).scalars().first()

    def find_all_ordered(self) -> list[Preset]:
        """Find all presets ordered by creation date"""
        stmt = select(Preset).order_by(Preset.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def find_paginated_with_count(
        self, limit: int = 10, offset: int = 0
    ) -> tuple[list[Preset], int]:
        """Find presets ordered by creation date with pagination"""
        if limit > self.MAX_LIMIT:
            raise ValueError(f"Limit cannot exceed {self.MAX_LIMIT}")

        count_stmt = select(func.count()).select_from(Preset)
        total = self.db.execute(count_stmt).scalar_one()

        stmt = select(Preset).order_by(Preset.created_at.desc()).limit(limit).offset(offset)
        items = list(self.db.execute(stmt).scalars().all())

        return items, total

    def unset_all_defaults(self, exclude_id: str | None = None) -> None:
        """Unset all default presets, optionally excluding one by ID"""
        stmt = select(Preset).where(Preset.is_default)
        if exclude_id:
            stmt = stmt.where(Preset.id != exclude_id)

        result = self.db.execute(stmt).scalars().all()
        for preset in result:
            preset.is_default = False
        self.db.flush()
