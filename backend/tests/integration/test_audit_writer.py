"""Audit-writer integration test (BE-M12c).

The ``AuditWriter`` opens its OWN ``AsyncSession`` (``AsyncSessionLocal``, bound to
``DATABASE_URL``) and commits independently of the request transaction, swallowing
all errors — audit logging must never break a request. These run against the real
Postgres container so that self-committing write is actually exercised: one test
asserts a row lands, the other that a write failure is swallowed, not propagated.
"""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from src.audit.repository_async import AuditRepository
from src.audit.writer import audit_logger
from src.core.config import settings
from src.core.persistence import gen_id
from src.core.persistence.models import LlmAuditLog

pytestmark = [pytest.mark.postgres, pytest.mark.integration]


def _enable_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings.logging, "audit_enabled", True)
    monkeypatch.setattr(settings.logging, "log_llm_calls", True)


@pytest.mark.asyncio
async def test_audit_writer_persists_llm_call(
    pg_sync_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An enabled writer commits the audit row on its own session."""
    _enable_audit(monkeypatch)
    marker = f"it-audit-{gen_id()}"

    try:
        await audit_logger.log_llm_call(
            chat_id=None,
            provider=marker,
            model="test-model",
            prompt_tokens=1,
            completion_tokens=2,
            total_tokens=3,
            latency_ms=1.0,
            status="success",
        )

        row = pg_sync_session.execute(
            select(LlmAuditLog).where(LlmAuditLog.provider == marker)
        ).scalar_one_or_none()
        assert row is not None  # the writer committed independently of the request
        assert row.total_tokens == 3
    finally:
        # The writer's own commit is outside the fixture transaction — clean it up.
        pg_sync_session.execute(delete(LlmAuditLog).where(LlmAuditLog.provider == marker))
        pg_sync_session.commit()


@pytest.mark.asyncio
async def test_audit_writer_swallows_write_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failing write is swallowed — the writer never propagates to the caller."""
    _enable_audit(monkeypatch)
    # Force the persist to blow up; _write must catch it and return normally.
    monkeypatch.setattr(AuditRepository, "add", AsyncMock(side_effect=RuntimeError("db down")))

    # Must NOT raise — audit logging can never break the request path.
    await audit_logger.log_llm_call(
        chat_id=None,
        provider="it-audit-failure",
        model="test-model",
        prompt_tokens=1,
        completion_tokens=2,
        total_tokens=3,
        latency_ms=1.0,
        status="success",
    )
