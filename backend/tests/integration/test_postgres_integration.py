"""PostgreSQL + VectorChord integration tests.

These run against a real Postgres container (DATABASE_URL) with the schema already
migrated via `alembic upgrade head`. They exercise the parts that cannot run on
SQLite: the VectorChord `<=>` cosine search over the vchordrq index, the retrieval
pipeline, and that seed data + migrations land correctly on real Postgres.

Embeddings are mocked (the embedding HTTP call is covered by unit tests); the
vector storage and search are real. Test vectors are padded to the pinned column
dimension (`DIM`); the leading components carry the direction under test, the
zero-padded tail leaves cosine similarity unchanged.
"""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from src.core.persistence.models import Embedding, ModelFamily, PromptTemplate, Provider
from src.fixtures.service import seed_database
from src.rag.embedding_service import EmbeddingService
from src.rag.models import DataBankEntry
from src.rag.repository import DataBankRepository
from src.rag.repository_async import AsyncEmbeddingRepository
from src.rag.retrieval_service import RetrievalService

# Both markers: `postgres` (needs a real PG+pgvector) and `integration` (so the
# `-m integration` suite run picks it up alongside the provider integration tests).
pytestmark = [pytest.mark.postgres, pytest.mark.integration]

# Matches the pinned `embeddings.embedding` column type (vector(768)).
DIM = 768


def _pad(prefix: list[float]) -> list[float]:
    """Extend a short direction vector to the pinned column dimension with zeros."""
    return prefix + [0.0] * (DIM - len(prefix))


def _embedding(
    source_id: str, vec: list[float], content: str, source_type: str = "message"
) -> Embedding:
    return Embedding(
        source_type=source_type,
        source_id=source_id,
        content_hash=abs(hash(content)) % (10**15),
        content=content,
        chunk_index=0,
        model_name="test-model",
        dimensions=len(vec),
        embedding=vec,
    )


def test_vectorchord_extension_and_schema(pg_sync_session: Session) -> None:
    """Migrations applied on real PG: vchord (on pgvector) and the vchordrq index exist."""
    extensions = set(
        pg_sync_session.execute(
            text("select extname from pg_extension where extname in ('vector', 'vchord')")
        )
        .scalars()
        .all()
    )
    assert {"vector", "vchord"} <= extensions

    # The embedding column is indexed by VectorChord's vchordrq access method.
    index_am = pg_sync_session.execute(
        text(
            "select am.amname from pg_class i "
            "join pg_index ix on ix.indexrelid = i.oid "
            "join pg_am am on am.oid = i.relam "
            "where i.relname = 'ix_embeddings_vchordrq'"
        )
    ).scalar_one_or_none()
    assert index_am == "vchordrq"

    tables = set(
        pg_sync_session.execute(
            text("select table_name from information_schema.tables where table_schema = 'public'")
        )
        .scalars()
        .all()
    )
    assert {"embeddings", "llm_audit_logs", "http_logs", "error_logs"} <= tables


@pytest.mark.asyncio
async def test_pgvector_search_ranking(pg_async_session: AsyncSession) -> None:
    """Real VectorChord cosine search ranks by closeness and honours the threshold.

    Uses data-bank embeddings (scoped by ``source_id``) so no chat/message FK rows
    are needed — the cosine ranking under test is source-type agnostic.
    """
    repo = AsyncEmbeddingRepository(pg_async_session)
    entry_id = "itdbrank1"
    await repo.create(_embedding(entry_id, _pad([1.0, 0.0, 0.0, 0.0]), "near", "data_bank"))
    await repo.create(_embedding(entry_id, _pad([0.8, 0.2, 0.0, 0.0]), "mid", "data_bank"))
    await repo.create(_embedding(entry_id, _pad([0.0, 0.0, 0.0, 1.0]), "far", "data_bank"))
    await pg_async_session.flush()

    rows = await repo.search_similar(
        query_embedding=_pad([1.0, 0.0, 0.0, 0.0]),
        chat_id="unused",
        data_bank_ids=[entry_id],
        limit=10,
        threshold=0.5,
    )

    contents = [r["content"] for r in rows]
    assert contents[0] == "near"  # closest ranked first
    assert "far" not in contents  # orthogonal vector filtered by threshold
    assert rows[0]["score"] >= rows[-1]["score"]  # descending similarity


@pytest.mark.asyncio
async def test_retrieval_service_mocked_embeddings(
    pg_async_session: AsyncSession, pg_sync_session: Session
) -> None:
    """End-to-end retrieve(): mocked query embedding + real VectorChord search over a
    global data-bank entry (resolved by scope, matched by source_id)."""
    repo = AsyncEmbeddingRepository(pg_async_session)
    data_bank_repo = DataBankRepository(pg_sync_session)
    entry = data_bank_repo.create(
        DataBankEntry(name="keep-lore", content="the dragon guards the keep", scope="global")
    )
    await repo.create(
        _embedding(entry.id, _pad([1.0, 0.0, 0.0, 0.0]), "the dragon guards the keep", "data_bank")
    )
    await pg_async_session.flush()

    mock_embed = EmbeddingService.__new__(EmbeddingService)
    mock_embed.embed_query = AsyncMock(return_value=_pad([1.0, 0.0, 0.0, 0.0]))

    service = RetrievalService(mock_embed, repo, data_bank_repo)
    results = await service.retrieve(
        chat_id="itretrieve01", query_text="who guards the keep?", threshold=0.5
    )

    assert any(r.content == "the dragon guards the keep" for r in results)
    mock_embed.embed_query.assert_awaited_once()


def test_seed_data_populates(pg_sync_session: Session) -> None:
    """seed_database() is idempotent and populates baseline reference data on PG."""
    seed_database()  # uses the global session bound to DATABASE_URL; commits

    assert pg_sync_session.execute(select(Provider).limit(1)).scalars().first() is not None
    assert pg_sync_session.execute(select(ModelFamily).limit(1)).scalars().first() is not None
    assert pg_sync_session.execute(select(PromptTemplate).limit(1)).scalars().first() is not None
