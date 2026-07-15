"""Tests for DataBankService"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.orm import Session
from src.core.exceptions import NotFoundError
from src.rag.repository import DataBankRepository
from src.rag.retrieval_service import RetrievalService
from src.rag.service import DataBankService
from src.rag.write_service import DataBankWriteService


def _make_service(db: Session) -> DataBankService:
    return DataBankService(DataBankRepository(db))


def _make_retrieval_mock() -> MagicMock:
    """A stand-in RetrievalService with the awaited write-path methods stubbed."""
    mock = MagicMock(spec=RetrievalService)
    mock.vectorize_data_bank_entry = AsyncMock(return_value=None)
    mock.remove_embeddings = AsyncMock(return_value=None)
    return mock


class TestDataBankCRUD:
    def test_create_entry(self, db: Session) -> None:
        service = _make_service(db)

        entry = service.create(
            name="World History",
            content="The kingdom fell in the year 1042.",
            scope="global",
        )

        assert entry.id is not None
        assert entry.name == "World History"
        assert entry.content == "The kingdom fell in the year 1042."
        assert entry.scope == "global"
        assert entry.character_id is None
        assert entry.chat_id is None

    def test_create_entry_with_character_scope(self, db: Session, sample_character) -> None:
        service = _make_service(db)

        entry = service.create(
            name="Character Lore",
            content="Alice was born in the northern wastes.",
            scope="character",
            character_id=sample_character.id,
        )

        assert entry.scope == "character"
        assert entry.character_id == sample_character.id

    def test_update_entry(self, db: Session) -> None:
        service = _make_service(db)

        entry = service.create(name="Original", content="Old info")
        updated = service.update(
            entry.id,
            name="Updated",
            content="New info",
            scope="character",
        )

        assert updated.name == "Updated"
        assert updated.content == "New info"
        assert updated.scope == "character"

    def test_update_entry_partial(self, db: Session) -> None:
        service = _make_service(db)

        entry = service.create(name="Keep Name", content="Keep Content", scope="global")
        updated = service.update(entry.id, content="Only content changed")

        assert updated.name == "Keep Name"
        assert updated.content == "Only content changed"
        assert updated.scope == "global"

    def test_delete_entry(self, db: Session) -> None:
        service = _make_service(db)

        entry = service.create(name="ToDelete", content="Bye")
        service.delete(entry.id)

        with pytest.raises(NotFoundError) as exc_info:
            service.get_by_id(entry.id)
        assert exc_info.value.status_code == 404

    def test_get_by_id_not_found(self, db: Session) -> None:
        service = _make_service(db)

        with pytest.raises(NotFoundError) as exc_info:
            service.get_by_id("nonexistent")
        assert exc_info.value.status_code == 404
        assert "Data bank entry not found" in exc_info.value.message


class TestDataBankListing:
    def test_list_all_entries(self, db: Session) -> None:
        service = _make_service(db)

        service.create(name="Entry A", content="A")
        service.create(name="Entry B", content="B")

        entries = service.list_entries()
        assert len(entries) == 2

    def test_list_by_scope_global(self, db: Session) -> None:
        service = _make_service(db)

        service.create(name="Global 1", content="A", scope="global")
        service.create(name="Global 2", content="B", scope="global")
        service.create(name="Character 1", content="C", scope="character")

        global_entries = service.list_entries(scope="global")
        assert len(global_entries) == 2
        assert all(e.scope == "global" for e in global_entries)

    def test_list_by_scope_character(self, db: Session, sample_character) -> None:
        service = _make_service(db)

        service.create(
            name="Char Entry",
            content="A",
            scope="character",
            character_id=sample_character.id,
        )
        service.create(name="Global Entry", content="B", scope="global")

        char_entries = service.list_entries(scope="character", character_id=sample_character.id)
        assert len(char_entries) == 1
        assert char_entries[0].character_id == sample_character.id

    def test_list_no_scope_returns_all(self, db: Session) -> None:
        service = _make_service(db)

        service.create(name="G1", content="A", scope="global")
        service.create(name="C1", content="B", scope="character")

        all_entries = service.list_entries()
        assert len(all_entries) == 2


class TestDataBankWriteService:
    """The async persist+index write-path (BE-H6)."""

    @pytest.mark.asyncio
    async def test_create_persists_and_indexes(self, db: Session) -> None:
        retrieval = _make_retrieval_mock()
        service = DataBankWriteService(_make_service(db), retrieval)

        entry = await service.create(name="Indexed", content="Embed me.")

        # Persisted...
        assert DataBankRepository(db).find_by_id(entry.id) is not None
        # ...and indexed in the same call.
        retrieval.vectorize_data_bank_entry.assert_awaited_once()
        kwargs = retrieval.vectorize_data_bank_entry.await_args.kwargs
        assert kwargs["entry_id"] == entry.id
        assert kwargs["content"] == "Embed me."

    @pytest.mark.asyncio
    async def test_create_survives_index_failure(self, db: Session) -> None:
        retrieval = _make_retrieval_mock()
        retrieval.vectorize_data_bank_entry.side_effect = RuntimeError("embed backend down")
        service = DataBankWriteService(_make_service(db), retrieval)

        entry = await service.create(name="Resilient", content="Still saved.")

        # Best-effort index: the failure is swallowed and the row persists.
        assert DataBankRepository(db).find_by_id(entry.id) is not None

    @pytest.mark.asyncio
    async def test_delete_purges_embeddings(self, db: Session) -> None:
        retrieval = _make_retrieval_mock()
        service = DataBankWriteService(_make_service(db), retrieval)
        entry = await service.create(name="Purge Me", content="x")
        retrieval.vectorize_data_bank_entry.reset_mock()

        await service.delete(entry.id)

        assert DataBankRepository(db).find_by_id(entry.id) is None
        retrieval.remove_embeddings.assert_awaited_once_with("data_bank", entry.id)

    @pytest.mark.asyncio
    async def test_create_without_retrieval_skips_indexing(self, db: Session) -> None:
        """RAG disabled (retrieval is None): the row persists, no embed attempted."""
        service = DataBankWriteService(_make_service(db), None)

        entry = await service.create(name="No RAG", content="x")

        assert DataBankRepository(db).find_by_id(entry.id) is not None
