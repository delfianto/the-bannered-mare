"""Tests for RetrievalService's rerank-and-cut behavior."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from src.rag.retrieval_service import RetrievalService, _content_hash
from src.rag.schemas import RetrievedChunk

_INT64_MAX = 2**63 - 1


def test_content_hash_fits_signed_bigint():
    """Every hash must fit the signed BIGINT column, or asyncpg rejects the insert.

    The raw top-64-bit SHA-256 slice overflows int8 for ~half of all inputs; this
    guards the 63-bit mask that fixed silently-dropped embeddings.
    """
    for i in range(500):
        assert 0 <= _content_hash(f"sample entry {i}") <= _INT64_MAX


def _chunk(content: str, score: float = 0.5) -> RetrievedChunk:
    return RetrievedChunk(
        content=content,
        source_type="data_bank",
        source_id="src",
        score=score,
        chunk_index=0,
    )


def _service(rerank: object) -> RetrievalService:
    return RetrievalService(
        embedding_service=MagicMock(),
        embedding_repo=MagicMock(),
        data_bank_repo=MagicMock(),
        rerank_service=rerank,  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_rerank_reorders_drops_below_threshold_and_stamps_score():
    rerank = AsyncMock()
    # Cross-encoder puts index 1 first; index 0 falls below the score floor.
    rerank.rerank.return_value = [(1, 0.91), (0, 0.12)]
    service = _service(rerank)
    chunks = [_chunk("A", score=0.5), _chunk("B", score=0.5)]

    out = await service._rerank("q", chunks, top_n=5, score_threshold=0.3)

    assert [c.content for c in out] == ["B"]  # index 1 kept (0.91); index 0 dropped (0.12 < 0.3)
    assert out[0].score == pytest.approx(0.91)  # score stamped from the reranker


@pytest.mark.asyncio
async def test_rerank_fails_open_to_vector_order():
    rerank = AsyncMock()
    rerank.rerank.side_effect = RuntimeError("reranker down")
    service = _service(rerank)
    chunks = [_chunk("A"), _chunk("B")]

    out = await service._rerank("q", chunks, top_n=5, score_threshold=0.3)

    assert out == chunks  # unchanged vector order, nothing dropped


@pytest.mark.asyncio
async def test_vectorize_message_stores_chat_id_and_scopes_dedup():
    """A message embedding is stamped with its chat_id, and dedup is chat-scoped so
    identical content in different chats is stored (and retrievable) separately."""
    embedding_repo = MagicMock()
    embedding_repo.delete_by_source = AsyncMock()
    embedding_repo.exists_by_hash = AsyncMock(return_value=False)
    embedding_repo.create = AsyncMock()
    embedding_repo.commit = AsyncMock()
    embedding_service = MagicMock()
    embedding_service.embed_documents = AsyncMock(return_value=[[0.1] * 768])

    service = RetrievalService(
        embedding_service=embedding_service,
        embedding_repo=embedding_repo,
        data_bank_repo=MagicMock(),
    )

    await service.vectorize_message(
        message_id="m1", chat_id="cA", content="hello", model_name="nomic", dimensions=768
    )

    assert embedding_repo.exists_by_hash.await_args.kwargs["chat_id"] == "cA"
    stored = embedding_repo.create.await_args.args[0]
    assert stored.source_type == "message"
    assert stored.source_id == "m1"
    assert stored.chat_id == "cA"


@pytest.mark.asyncio
async def test_vectorize_message_replaces_prior_embedding():
    """Edit/regenerate re-vectorize: the message's prior embedding is always deleted
    first (replace semantics), so a stale pre-edit vector can never be retrieved —
    even when the new content dedups against another message and no insert happens."""
    embedding_repo = MagicMock()
    embedding_repo.delete_by_source = AsyncMock()
    # Dedup hit: identical content already embedded elsewhere in the chat.
    embedding_repo.exists_by_hash = AsyncMock(return_value=True)
    embedding_repo.create = AsyncMock()
    embedding_repo.commit = AsyncMock()
    embedding_service = MagicMock()
    embedding_service.embed_documents = AsyncMock(return_value=[[0.1] * 768])

    service = RetrievalService(
        embedding_service=embedding_service,
        embedding_repo=embedding_repo,
        data_bank_repo=MagicMock(),
    )

    await service.vectorize_message(
        message_id="m1", chat_id="cA", content="edited", model_name="nomic", dimensions=768
    )

    # The old vector is cleared regardless of the dedup outcome...
    embedding_repo.delete_by_source.assert_awaited_once_with("message", "m1")
    # ...but no duplicate is inserted when the content already exists in the chat.
    embedding_repo.create.assert_not_awaited()
    embedding_repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_retrieve_scopes_messages_by_chat_and_data_bank_by_ids():
    """retrieve() passes the chat_id (message scope) and resolved data-bank entry
    ids (data_bank scope) to the vector search."""
    embedding_service = MagicMock()
    embedding_service.embed_query = AsyncMock(return_value=[0.1] * 768)
    embedding_repo = MagicMock()
    embedding_repo.search_similar = AsyncMock(return_value=[])
    data_bank_repo = MagicMock()
    entry = MagicMock()
    entry.id = "db1"
    data_bank_repo.find_by_scope.return_value = [entry]

    service = RetrievalService(
        embedding_service=embedding_service,
        embedding_repo=embedding_repo,
        data_bank_repo=data_bank_repo,
    )

    await service.retrieve(chat_id="cA", query_text="q", character_id=None)

    kwargs = embedding_repo.search_similar.await_args.kwargs
    assert kwargs["chat_id"] == "cA"
    assert "db1" in kwargs["data_bank_ids"]
