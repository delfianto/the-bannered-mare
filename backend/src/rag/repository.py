"""Data access layer for DataBankEntry entities"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.persistence import BaseRepository
from src.rag.models import DataBankEntry


class DataBankRepository(BaseRepository[DataBankEntry]):
    """Repository for DataBankEntry data access"""

    def __init__(self, db: Session):
        super().__init__(db, DataBankEntry)

    def find_by_scope(
        self,
        scope: str,
        character_id: str | None = None,
        chat_id: str | None = None,
    ) -> list[DataBankEntry]:
        """Find entries filtered by scope and optional foreign keys."""
        stmt = select(DataBankEntry).where(DataBankEntry.scope == scope)
        if character_id is not None:
            stmt = stmt.where(DataBankEntry.character_id == character_id)
        if chat_id is not None:
            stmt = stmt.where(DataBankEntry.chat_id == chat_id)
        stmt = stmt.order_by(DataBankEntry.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())
