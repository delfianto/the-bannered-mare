"""Async retrieval service orchestrating the full RAG pipeline."""

import hashlib

from src.core.logging.logger_config import get_logger
from src.core.persistence import gen_id
from src.rag.chunker import chunk_text
from src.rag.embedding_service import EmbeddingService
from src.rag.models import Embedding
from src.rag.repository import DataBankRepository
from src.rag.repository_async import AsyncEmbeddingRepository
from src.rag.rerank_service import RerankService
from src.rag.schemas import RetrievedChunk

logger = get_logger(__name__)


def _content_hash(text: str) -> int:
    """Deterministic 63-bit hash for dedup.

    Masked to 63 bits so it always fits the signed BIGINT content_hash column:
    the top 16 hex digits of SHA-256 span the full *unsigned* 64-bit range and
    overflow Postgres int8 (asyncpg raises DataError) for ~half of all inputs,
    which silently dropped those chunks from the index.
    """
    return int(hashlib.sha256(text.encode()).hexdigest()[:16], 16) & 0x7FFFFFFFFFFFFFFF


class RetrievalService:
    """Orchestrates embedding, storage, and semantic search."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        embedding_repo: AsyncEmbeddingRepository,
        data_bank_repo: DataBankRepository,
        rerank_service: RerankService | None = None,
    ):
        self.embedding_service = embedding_service
        self.embedding_repo = embedding_repo
        self.data_bank_repo = data_bank_repo
        self.rerank_service = rerank_service

    async def retrieve(
        self,
        chat_id: str,
        query_text: str,
        character_id: str | None = None,
        max_results: int = 5,
        threshold: float = 0.3,
    ) -> list[RetrievedChunk]:
        """Embed query, search vectors, return top-K results."""
        query_vec = await self.embedding_service.embed_query(query_text)

        source_types = ["message", "data_bank"]
        source_ids = [chat_id]

        # Include data bank entries scoped to this chat, character, or global
        scopes = ["global"]
        if character_id:
            scopes.append("character")
        scopes.append("chat")

        entries = []
        for scope in scopes:
            if scope == "character" and character_id:
                entries.extend(self.data_bank_repo.find_by_scope(scope, character_id=character_id))
            elif scope == "chat":
                entries.extend(self.data_bank_repo.find_by_scope(scope, chat_id=chat_id))
            else:
                entries.extend(self.data_bank_repo.find_by_scope(scope))

        source_ids.extend(e.id for e in entries)

        # With a reranker, cast a wide net: pull up to `candidates` hits with no
        # vector similarity floor and let the cross-encoder decide relevance
        # (the reranker score_threshold becomes the floor instead).
        rerank_service = self.rerank_service
        if rerank_service is not None:
            search_limit = max(max_results, rerank_service.settings.candidates)
            search_threshold = 0.0
        else:
            search_limit = max_results
            search_threshold = threshold

        rows = await self.embedding_repo.search_similar(
            query_embedding=query_vec,
            source_types=source_types,
            source_ids=source_ids,
            limit=search_limit,
            threshold=search_threshold,
        )

        chunks = [
            RetrievedChunk(
                content=row["content"],
                source_type=row["source_type"],
                source_id=row["source_id"],
                score=row["score"],
                chunk_index=row["chunk_index"],
            )
            for row in rows
        ]

        if rerank_service is not None and chunks:
            chunks = await self._rerank(
                query_text, chunks, max_results, rerank_service.settings.score_threshold
            )

        return chunks[:max_results]

    async def _rerank(
        self,
        query_text: str,
        chunks: list[RetrievedChunk],
        top_n: int,
        score_threshold: float,
    ) -> list[RetrievedChunk]:
        """Reorder candidates with the cross-encoder, dropping those below threshold.

        Reranking is a quality boost, not a correctness requirement, so a down or
        slow reranker must never break retrieval — fall back to the vector ranking.
        Surviving chunks carry the reranker score so callers see the new basis for
        the order.
        """
        if self.rerank_service is None:
            return chunks
        try:
            ranked = await self.rerank_service.rerank(
                query_text, [c.content for c in chunks], top_n=top_n
            )
        except Exception:
            logger.warning("rerank_failed", exc_info=True)
            return chunks
        return [
            chunks[i].model_copy(update={"score": score})
            for i, score in ranked
            if score >= score_threshold
        ]

    async def vectorize_message(
        self,
        message_id: str,
        content: str,
        model_name: str,
        dimensions: int,
    ) -> None:
        """Embed and store a single message. Skip if hash already exists."""
        content_hash = _content_hash(content)
        if await self.embedding_repo.exists_by_hash(content_hash, "message"):
            return

        embeddings = await self.embedding_service.embed_documents([content])

        entity = Embedding(
            id=gen_id(),
            source_type="message",
            source_id=message_id,
            content_hash=content_hash,
            content=content,
            chunk_index=0,
            model_name=model_name,
            dimensions=dimensions,
            embedding=embeddings[0],
        )
        await self.embedding_repo.create(entity)
        await self.embedding_repo.commit()

    async def vectorize_data_bank_entry(
        self,
        entry_id: str,
        content: str,
        model_name: str,
        dimensions: int,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> None:
        """Chunk, embed, and store a data bank entry."""
        await self.embedding_repo.delete_by_source("data_bank", entry_id)

        chunks = chunk_text(content, max_size=chunk_size, overlap=chunk_overlap)
        if not chunks:
            return

        embeddings = await self.embedding_service.embed_documents(chunks)

        for idx, (chunk, vec) in enumerate(zip(chunks, embeddings, strict=True)):
            entity = Embedding(
                id=gen_id(),
                source_type="data_bank",
                source_id=entry_id,
                content_hash=_content_hash(chunk),
                content=chunk,
                chunk_index=idx,
                model_name=model_name,
                dimensions=dimensions,
                embedding=vec,
            )
            await self.embedding_repo.create(entity)

        await self.embedding_repo.commit()

    async def remove_embeddings(self, source_type: str, source_id: str) -> None:
        """Delete all stored embeddings for a source (e.g. a removed data-bank entry)."""
        await self.embedding_repo.delete_by_source(source_type, source_id)
        await self.embedding_repo.commit()
