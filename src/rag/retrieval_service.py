"""Async retrieval service orchestrating the full RAG pipeline."""

import hashlib

from src.core.persistence import gen_id
from src.rag.chunker import chunk_text
from src.rag.embedding_service import EmbeddingService
from src.rag.models import Embedding
from src.rag.repository import DataBankRepository
from src.rag.repository_async import AsyncEmbeddingRepository
from src.rag.schemas import RetrievedChunk


def _content_hash(text: str) -> int:
    """Deterministic 64-bit hash for dedup."""
    return int(hashlib.sha256(text.encode()).hexdigest()[:16], 16)


class RetrievalService:
    """Orchestrates embedding, storage, and semantic search."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        embedding_repo: AsyncEmbeddingRepository,
        data_bank_repo: DataBankRepository,
    ):
        self.embedding_service = embedding_service
        self.embedding_repo = embedding_repo
        self.data_bank_repo = data_bank_repo

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

        rows = await self.embedding_repo.search_similar(
            query_embedding=query_vec,
            source_types=source_types,
            source_ids=source_ids,
            limit=max_results,
            threshold=threshold,
        )

        return [
            RetrievedChunk(
                content=row["content"],
                source_type=row["source_type"],
                source_id=row["source_id"],
                score=row["score"],
                chunk_index=row["chunk_index"],
            )
            for row in rows
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
