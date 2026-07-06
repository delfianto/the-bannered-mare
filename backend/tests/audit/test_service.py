"""Tests for AuditQueryService (read side, Pydantic shaping)"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.audit.repository_async import AuditRepository
from src.audit.service import AuditQueryService
from src.core.persistence.models import LlmAuditLog


@pytest.mark.asyncio
async def test_query_llm_returns_dtos(async_db_session: AsyncSession) -> None:
    repo = AuditRepository(async_db_session)
    await repo.add(
        LlmAuditLog(
            chat_id="c1",
            provider="openai",
            model="gpt-4o",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            latency_ms=42.0,
            status="success",
            request_payload=[{"role": "user", "content": "hi"}],
            response_payload={"content": "yo", "finish_reason": "stop"},
        )
    )
    await async_db_session.commit()

    service = AuditQueryService(repo)
    page = await service.query_llm(limit=10, skip=0)
    assert page.total == 1
    assert page.logs[0].provider == "openai"
    assert page.logs[0].request_payload == [{"role": "user", "content": "hi"}]
    assert page.logs[0].response_payload == {"content": "yo", "finish_reason": "stop"}


@pytest.mark.asyncio
async def test_llm_stats_success_rate(async_db_session: AsyncSession) -> None:
    repo = AuditRepository(async_db_session)
    for status in ("success", "success", "success", "error"):
        await repo.add(
            LlmAuditLog(
                chat_id="c1",
                provider="openai",
                model="gpt-4o",
                prompt_tokens=1,
                completion_tokens=1,
                total_tokens=2,
                latency_ms=10.0,
                status=status,
                request_payload=[],
            )
        )
    await async_db_session.commit()

    service = AuditQueryService(repo)
    result = await service.llm_stats()
    assert len(result.stats) == 1
    stat = result.stats[0]
    assert stat.total_calls == 4
    assert stat.success_count == 3
    assert stat.error_count == 1
    assert stat.success_rate == 75.0
