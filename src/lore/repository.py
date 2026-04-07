"""Data access layer for lorebook entities"""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from src.core.persistence.base_repository import BaseRepository
from src.lore.models import Lorebook, LoreEntry


class LoreRepository(BaseRepository[Lorebook]):
    """Repository for Lorebook data access"""

    def __init__(self, db: Session):
        super().__init__(db, Lorebook)

    def find_by_character_id(self, character_id: str) -> list[Lorebook]:
        """Find all lorebooks for a specific character"""
        stmt = select(Lorebook).where(Lorebook.character_id == character_id)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    def find_global(self) -> list[Lorebook]:
        """Find all global lorebooks"""
        stmt = select(Lorebook).where(Lorebook.is_global.is_(True))
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    def find_by_id_with_entries(self, lorebook_id: str) -> Lorebook | None:
        """Find lorebook with entries eagerly loaded"""
        stmt = (
            select(Lorebook).where(Lorebook.id == lorebook_id).options(joinedload(Lorebook.entries))
        )
        result = self.db.execute(stmt)
        return result.scalars().first()

    def find_for_character_with_entries(self, character_id: str) -> list[Lorebook]:
        """Find character-specific + global lorebooks with entries loaded"""
        stmt = (
            select(Lorebook)
            .where((Lorebook.character_id == character_id) | (Lorebook.is_global.is_(True)))
            .options(joinedload(Lorebook.entries))
        )
        result = self.db.execute(stmt)
        return list(result.scalars().unique().all())


class LoreEntryRepository(BaseRepository[LoreEntry]):
    """Repository for LoreEntry data access"""

    def __init__(self, db: Session):
        super().__init__(db, LoreEntry)

    def find_by_lorebook_id(self, lorebook_id: str) -> list[LoreEntry]:
        """Find all entries for a lorebook ordered by display order"""
        stmt = (
            select(LoreEntry)
            .where(LoreEntry.lorebook_id == lorebook_id)
            .order_by(LoreEntry.order.asc())
        )
        result = self.db.execute(stmt)
        return list(result.scalars().all())
