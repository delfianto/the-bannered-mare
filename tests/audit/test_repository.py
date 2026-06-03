"""Tests for AuditRepository (insert + query + stats) on the async test DB"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.audit.repository_async import AuditRepository
from src.core.persistence.models import ErrorLog, HttpLog, LlmAuditLog


def _llm(provider: str, model: str, status: str = "success", total: int = 10) -> LlmAuditLog:
    return LlmAuditLog(
        chat_id="chat-1",
        provider=provider,
        model=model,
        prompt_tokens=total // 2,
        completion_tokens=total - total // 2,
        total_tokens=total,
        latency_ms=100.0,
        status=status,
        request_payload=[{"role": "user", "content": "hi"}],
        response_payload={"content": "hello", "finish_reason": "stop"}
        if status == "success"
        else None,
    )


@pytest.mark.asyncio
async def test_add_and_query_llm(async_db_session: AsyncSession) -> None:
    repo = AuditRepository(async_db_session)
    await repo.add(_llm("openai", "gpt-4o"))
    await repo.add(_llm("anthropic", "claude", status="error"))
    await async_db_session.commit()

    rows, total = await repo.query_llm(limit=10, offset=0)
    assert total == 2
    # JSONB round-trips as a dict/list
    assert rows[0].request_payload == [{"role": "user", "content": "hi"}]

    rows, total = await repo.query_llm(limit=10, offset=0, provider="openai")
    assert total == 1
    assert rows[0].model == "gpt-4o"

    rows, total = await repo.query_llm(limit=10, offset=0, status="error")
    assert total == 1
    assert rows[0].response_payload is None


@pytest.mark.asyncio
async def test_query_llm_model_ilike_and_pagination(async_db_session: AsyncSession) -> None:
    repo = AuditRepository(async_db_session)
    for i in range(5):
        await repo.add(_llm("openai", f"gpt-4o-{i}"))
    await async_db_session.commit()

    rows, total = await repo.query_llm(limit=2, offset=0, model="GPT-4O")  # case-insensitive
    assert total == 5
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_llm_stats_aggregation(async_db_session: AsyncSession) -> None:
    repo = AuditRepository(async_db_session)
    await repo.add(_llm("openai", "gpt-4o", total=10))
    await repo.add(_llm("openai", "gpt-4o", total=20))
    await repo.add(_llm("openai", "gpt-4o", status="error", total=0))
    await async_db_session.commit()

    stats = await repo.llm_stats()
    assert len(stats) == 1
    row = stats[0]
    assert row["provider"] == "openai"
    assert row["total_calls"] == 3
    assert row["total_tokens"] == 30
    assert row["success_count"] == 2
    assert row["error_count"] == 1


@pytest.mark.asyncio
async def test_query_http_and_errors(async_db_session: AsyncSession) -> None:
    repo = AuditRepository(async_db_session)
    await repo.add(
        HttpLog(request_id="r1", method="GET", path="/a", status_code=200, latency_ms=1.0)
    )
    await repo.add(
        HttpLog(request_id="r2", method="POST", path="/b", status_code=500, latency_ms=2.0)
    )
    await repo.add(ErrorLog(error_type="ValueError", message="boom", context={"k": "v"}))
    await async_db_session.commit()

    rows, total = await repo.query_http(limit=10, offset=0, status_code=500)
    assert total == 1
    assert rows[0].path == "/b"

    rows, total = await repo.query_http(limit=10, offset=0, path="/a")
    assert total == 1

    rows, total = await repo.query_errors(limit=10, offset=0, error_type="ValueError")
    assert total == 1
    assert rows[0].context == {"k": "v"}
