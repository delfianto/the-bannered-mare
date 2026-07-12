"""Data Bank CRUD business logic service"""

from src.core.base_service import get_or_404
from src.core.persistence import gen_id
from src.rag.models import DataBankEntry
from src.rag.repository import DataBankRepository


class DataBankService:
    """Service for data bank entry CRUD operations"""

    def __init__(self, repo: DataBankRepository):
        self.repo = repo

    def list_entries(
        self,
        scope: str | None = None,
        character_id: str | None = None,
        chat_id: str | None = None,
    ) -> list[DataBankEntry]:
        """List entries with optional scope filtering."""
        if scope is not None:
            return self.repo.find_by_scope(scope, character_id=character_id, chat_id=chat_id)
        return self.repo.find_all_ordered()

    def get_by_id(self, entry_id: str) -> DataBankEntry:
        """Get entry by ID, raise 404 if not found."""
        return get_or_404(self.repo, entry_id, "Data bank entry")

    def create(
        self,
        name: str,
        content: str,
        scope: str = "global",
        character_id: str | None = None,
        chat_id: str | None = None,
    ) -> DataBankEntry:
        """Create a new data bank entry."""
        entry = DataBankEntry(
            id=gen_id(),
            name=name,
            content=content,
            scope=scope,
            character_id=character_id,
            chat_id=chat_id,
        )
        created = self.repo.create(entry)
        self.repo.commit()
        return created

    def update(
        self,
        entry_id: str,
        name: str | None = None,
        content: str | None = None,
        scope: str | None = None,
    ) -> DataBankEntry:
        """Update an existing data bank entry."""
        entry = self.get_by_id(entry_id)

        if name is not None:
            entry.name = name
        if content is not None:
            entry.content = content
        if scope is not None:
            entry.scope = scope

        updated = self.repo.update(entry)
        self.repo.commit()
        return updated

    def delete(self, entry_id: str) -> None:
        """Delete a data bank entry."""
        entry = self.get_by_id(entry_id)
        self.repo.delete(entry)
        self.repo.commit()
