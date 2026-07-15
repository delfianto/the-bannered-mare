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
from src.core.persistence.models import (
    Character,
    Chat,
    Embedding,
    ModelFamily,
    PromptTemplate,
    Provider,
)
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


# --- BE-H3 part 2: vchordrq tuning, message scoping, threshold edge, empty results ---


@pytest.mark.asyncio
async def test_vchordrq_tuning_applied(pg_async_session: AsyncSession) -> None:
    """`_apply_vchordrq_tuning` sets the search GUCs on the transaction (best-effort)."""
    repo = AsyncEmbeddingRepository(pg_async_session)

    await repo._apply_vchordrq_tuning(epsilon=0.5, max_scan_tuples=100)  # pyright: ignore[reportPrivateUsage]

    eps = (
        await pg_async_session.execute(text("SELECT current_setting('vchordrq.epsilon', true)"))
    ).scalar_one()
    mst = (
        await pg_async_session.execute(
            text("SELECT current_setting('vchordrq.max_scan_tuples', true)")
        )
    ).scalar_one()
    assert eps == "0.5"
    assert mst == "100"

    # None values are skipped (and never raise) — the savepoint isolates each SET LOCAL.
    await repo._apply_vchordrq_tuning(epsilon=None, max_scan_tuples=None)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_message_embeddings_scoped_by_chat(pg_async_session: AsyncSession) -> None:
    """Message-embedding search is scoped to its ``chat_id`` — another chat's identical
    vector is not returned."""
    char = Character(name="Scoper")
    pg_async_session.add(char)
    await pg_async_session.flush()
    chat_a = Chat(character_id=char.id, title="A")
    chat_b = Chat(character_id=char.id, title="B")
    pg_async_session.add_all([chat_a, chat_b])
    await pg_async_session.flush()

    repo = AsyncEmbeddingRepository(pg_async_session)
    emb_a = _embedding("msg-a", _pad([1.0, 0.0, 0.0, 0.0]), "alpha history", "message")
    emb_a.chat_id = chat_a.id
    emb_b = _embedding("msg-b", _pad([1.0, 0.0, 0.0, 0.0]), "beta history", "message")
    emb_b.chat_id = chat_b.id
    await repo.create(emb_a)
    await repo.create(emb_b)
    await pg_async_session.flush()

    rows = await repo.search_similar(
        query_embedding=_pad([1.0, 0.0, 0.0, 0.0]),
        chat_id=chat_a.id,
        data_bank_ids=[],
        limit=10,
        threshold=0.5,
    )

    contents = [r["content"] for r in rows]
    assert "alpha history" in contents
    assert "beta history" not in contents  # belongs to chat_b — scoped out


@pytest.mark.asyncio
async def test_search_threshold_equality_edge(pg_async_session: AsyncSession) -> None:
    """A hit whose similarity exactly equals the threshold is kept (the `>=` boundary)."""
    repo = AsyncEmbeddingRepository(pg_async_session)
    entry_id = "itedge1"
    await repo.create(_embedding(entry_id, _pad([1.0, 0.0, 0.0, 0.0]), "identical", "data_bank"))
    await repo.create(_embedding(entry_id, _pad([0.0, 1.0, 0.0, 0.0]), "orthogonal", "data_bank"))
    await pg_async_session.flush()

    # Query identical to "identical" → cosine similarity is exactly 1.0.
    rows = await repo.search_similar(
        query_embedding=_pad([1.0, 0.0, 0.0, 0.0]),
        chat_id="unused",
        data_bank_ids=[entry_id],
        limit=10,
        threshold=1.0,
    )

    contents = [r["content"] for r in rows]
    assert "identical" in contents  # score == threshold (1.0) → included
    assert "orthogonal" not in contents  # score 0.0 < 1.0 → excluded


@pytest.mark.asyncio
async def test_search_returns_empty_when_no_matches(pg_async_session: AsyncSession) -> None:
    """No in-scope embeddings (empty data-bank scope + a chat with none) → empty list."""
    repo = AsyncEmbeddingRepository(pg_async_session)

    rows = await repo.search_similar(
        query_embedding=_pad([1.0, 0.0, 0.0, 0.0]),
        chat_id="no-such-chat",
        data_bank_ids=[],
        limit=10,
        threshold=0.5,
    )

    assert rows == []
