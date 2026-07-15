"""Data Bank CRUD business logic service"""

from src.core.base_service import BaseCrudService, apply_update
from src.core.persistence import UnitOfWork, gen_id
from src.rag.models import DataBankEntry
from src.rag.repository import DataBankRepository

_EDITABLE = {"name", "content", "scope"}


class DataBankService(BaseCrudService[DataBankEntry, DataBankRepository]):
    """Service for data bank entry CRUD operations (inherits get_by_id/delete)."""

    def __init__(self, repo: DataBankRepository, uow: UnitOfWork | None = None):
        super().__init__(repo, uow or UnitOfWork(repo.db), "Data bank entry")

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
        self.uow.commit()
        return created

    def update(
        self,
        entry_id: str,
        name: str | None = None,
        content: str | None = None,
        scope: str | None = None,
    ) -> DataBankEntry:
        """Update an existing data bank entry (skip-on-None: only provided fields change)."""
        entry = self.get_by_id(entry_id)
        patch = {"name": name, "content": content, "scope": scope}
        apply_update(entry, {k: v for k, v in patch.items() if v is not None}, _EDITABLE)
        updated = self.repo.update(entry)
        self.uow.commit()
        return updated
