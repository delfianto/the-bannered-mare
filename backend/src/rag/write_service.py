"""Async write-path for data-bank entries: persist + (re)index / purge as one operation.

Data-bank rows persist through the sync ``DataBankService``; their embeddings are
built by the async ``RetrievalService``. This service owns that two-phase workflow
— including the best-effort indexing (a failed embed never fails the CRUD; the row
persists and re-indexes on the next update) — so the router calls one method per
operation instead of orchestrating persist-then-index itself (BE-H6).
"""

from src.core.config import settings
from src.core.logging.logger_config import get_logger
from src.rag.models import DataBankEntry
from src.rag.retrieval_service import RetrievalService
from src.rag.service import DataBankService

logger = get_logger(__name__)


class DataBankWriteService:
    """Persist + (re)index / purge data-bank entries as a single operation."""

    def __init__(self, data_bank: DataBankService, retrieval: RetrievalService | None):
        self.data_bank = data_bank
        # None when RAG is disabled — persistence still works; indexing is skipped.
        self.retrieval = retrieval

    async def create(
        self,
        name: str,
        content: str,
        scope: str = "global",
        character_id: str | None = None,
        chat_id: str | None = None,
    ) -> DataBankEntry:
        """Create an entry and index it for retrieval (when RAG is enabled)."""
        entry = self.data_bank.create(
            name=name,
            content=content,
            scope=scope,
            character_id=character_id,
            chat_id=chat_id,
        )
        await self._index(entry)
        return entry

    async def update(
        self,
        entry_id: str,
        name: str | None = None,
        content: str | None = None,
        scope: str | None = None,
    ) -> DataBankEntry:
        """Update an entry and re-index it (when RAG is enabled)."""
        entry = self.data_bank.update(entry_id=entry_id, name=name, content=content, scope=scope)
        # vectorize_data_bank_entry purges the old chunks first, so this re-indexes cleanly.
        await self._index(entry)
        return entry

    async def delete(self, entry_id: str) -> None:
        """Delete an entry and purge its embeddings (best-effort)."""
        self.data_bank.delete(entry_id)
        if self.retrieval is None:
            return
        try:
            await self.retrieval.remove_embeddings("data_bank", entry_id)
        except Exception:
            logger.warning("data_bank_embedding_purge_failed", entry_id=entry_id, exc_info=True)

    async def _index(self, entry: DataBankEntry) -> None:
        """Chunk and embed an entry for retrieval (best-effort; the row is already saved).

        No-op when RAG is disabled (retrieval is None). A failed embed must not fail
        the CRUD request — the entry persists and can be re-indexed on next update.
        """
        if self.retrieval is None:
            return
        try:
            await self.retrieval.vectorize_data_bank_entry(
                entry_id=entry.id,
                content=entry.content,
                model_name=settings.rag.embedding.model,
                dimensions=settings.rag.embedding.dimensions,
                chunk_size=settings.rag.chunk_size,
                chunk_overlap=settings.rag.chunk_overlap,
            )
        except Exception:
            logger.warning("data_bank_vectorize_failed", entry_id=entry.id, exc_info=True)
