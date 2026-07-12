"""Data access layer for Profile entities"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.persistence import BaseRepository
from src.profile.models import Profile


class ProfileRepository(BaseRepository[Profile]):
    """Repository for Profile data access with custom queries"""

    def __init__(self, db: Session):
        super().__init__(db, Profile)

    def find_by_name(self, name: str) -> Profile | None:
        """Find a profile by its unique name"""
        stmt = select(Profile).where(Profile.name == name)
        return self.db.execute(stmt).scalars().first()

    def find_all_ordered(self) -> list[Profile]:
        """Find all profiles ordered by creation date"""
        stmt = select(Profile).order_by(Profile.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def find_paginated_with_count(
        self, limit: int = 10, offset: int = 0
    ) -> tuple[list[Profile], int]:
        """Find profiles ordered by creation date with pagination"""
        if limit > self.MAX_LIMIT:
            raise ValueError(f"Limit cannot exceed {self.MAX_LIMIT}")

        count_stmt = select(func.count()).select_from(Profile)
        total = self.db.execute(count_stmt).scalar_one()

        stmt = select(Profile).order_by(Profile.created_at.desc()).limit(limit).offset(offset)
        items = list(self.db.execute(stmt).scalars().all())

        return items, total

    def unset_all_defaults(self, exclude_id: str | None = None) -> None:
        """Unset all default profiles, optionally excluding one by ID"""
        stmt = select(Profile).where(Profile.is_default)
        if exclude_id:
            stmt = stmt.where(Profile.id != exclude_id)

        result = self.db.execute(stmt).scalars().all()
        for profile in result:
            profile.is_default = False
        self.db.flush()
