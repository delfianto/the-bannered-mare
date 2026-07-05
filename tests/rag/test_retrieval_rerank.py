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
        assert 0 <= _content_hash(f"candlekeep entry {i}") <= _INT64_MAX


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
