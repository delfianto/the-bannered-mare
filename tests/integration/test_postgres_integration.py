"""PostgreSQL + pgvector integration tests.

These run against a real Postgres container (DATABASE_URL) with the schema already
migrated via `alembic upgrade head`. They exercise the parts that cannot run on
SQLite: the pgvector `<=>` similarity search, the retrieval pipeline, and that
seed data + migrations land correctly on real Postgres.

Embeddings are mocked (the embedding HTTP call is covered by unit tests); the
vector storage and search are real.
"""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from src.core.persistence.models import Embedding, ModelFamily, PromptTemplate, Provider
from src.fixtures.service import seed_database
from src.rag.embedding_service import EmbeddingService
from src.rag.repository import DataBankRepository
from src.rag.repository_async import AsyncEmbeddingRepository
from src.rag.retrieval_service import RetrievalService

pytestmark = pytest.mark.postgres


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


def test_vector_extension_and_schema(pg_sync_session: Session) -> None:
    """Migrations applied on real PG: the `vector` extension and key tables exist."""
    ext = pg_sync_session.execute(
        text("select extname from pg_extension where extname = 'vector'")
    ).scalar_one_or_none()
    assert ext == "vector"

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
    """Real pgvector cosine search ranks by closeness and honours the threshold."""
    repo = AsyncEmbeddingRepository(pg_async_session)
    chat_id = "itchatrank1"
    await repo.create(_embedding(chat_id, [1.0, 0.0, 0.0, 0.0], "near"))
    await repo.create(_embedding(chat_id, [0.8, 0.2, 0.0, 0.0], "mid"))
    await repo.create(_embedding(chat_id, [0.0, 0.0, 0.0, 1.0], "far"))
    await pg_async_session.flush()

    rows = await repo.search_similar(
        query_embedding=[1.0, 0.0, 0.0, 0.0],
        source_types=["message"],
        source_ids=[chat_id],
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
    """End-to-end retrieve(): mocked query embedding + real pgvector search."""
    chat_id = "itretrieve01"
    repo = AsyncEmbeddingRepository(pg_async_session)
    await repo.create(_embedding(chat_id, [1.0, 0.0, 0.0, 0.0], "the dragon guards the keep"))
    await pg_async_session.flush()

    mock_embed = EmbeddingService.__new__(EmbeddingService)
    mock_embed.embed = AsyncMock(return_value=[[1.0, 0.0, 0.0, 0.0]])

    service = RetrievalService(mock_embed, repo, DataBankRepository(pg_sync_session))
    results = await service.retrieve(
        chat_id=chat_id, query_text="who guards the keep?", threshold=0.5
    )

    assert any(r.content == "the dragon guards the keep" for r in results)
    mock_embed.embed.assert_awaited_once()


def test_seed_data_populates(pg_sync_session: Session) -> None:
    """seed_database() is idempotent and populates baseline reference data on PG."""
    seed_database()  # uses the global session bound to DATABASE_URL; commits

    assert pg_sync_session.execute(select(Provider).limit(1)).scalars().first() is not None
    assert pg_sync_session.execute(select(ModelFamily).limit(1)).scalars().first() is not None
    assert pg_sync_session.execute(select(PromptTemplate).limit(1)).scalars().first() is not None
