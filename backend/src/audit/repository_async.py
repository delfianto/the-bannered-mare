"""Async data access for audit-log tables (LLM calls, HTTP requests, errors)"""

from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.persistence.models import ErrorLog, HttpLog, LlmAuditLog


class AuditRepository:
    """Async repository for the three audit-log tables.

    Spans multiple models, so it does not extend AsyncBaseRepository; it exposes
    explicit insert and query helpers instead.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def add(self, entity: LlmAuditLog | HttpLog | ErrorLog) -> None:
        """Persist a single audit record (caller controls the transaction)."""
        self.db.add(entity)
        await self.db.flush()

    async def query_llm(
        self,
        *,
        limit: int,
        offset: int,
        chat_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        status: str | None = None,
    ) -> tuple[list[LlmAuditLog], int]:
        """Return a page of LLM audit logs (newest first) and the total count."""
        filters: list[ColumnElement[bool]] = []
        if chat_id:
            filters.append(LlmAuditLog.chat_id == chat_id)
        if provider:
            filters.append(LlmAuditLog.provider == provider)
        if model:
            filters.append(LlmAuditLog.model.ilike(f"%{model}%"))
        if status:
            filters.append(LlmAuditLog.status == status)

        stmt = (
            select(LlmAuditLog)
            .where(*filters)
            .order_by(LlmAuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        total = (
            await self.db.execute(select(func.count()).select_from(LlmAuditLog).where(*filters))
        ).scalar_one()
        return rows, total

    async def llm_stats(
        self, *, start: datetime | None = None, end: datetime | None = None
    ) -> list[dict[str, Any]]:
        """Aggregate usage per provider/model, optionally within a time window."""
        filters: list[ColumnElement[bool]] = []
        if start:
            filters.append(LlmAuditLog.created_at >= start)
        if end:
            filters.append(LlmAuditLog.created_at <= end)

        total_tokens = func.coalesce(func.sum(LlmAuditLog.total_tokens), 0)
        stmt = (
            select(
                LlmAuditLog.provider,
                LlmAuditLog.model,
                func.count().label("total_calls"),
                func.coalesce(func.sum(LlmAuditLog.prompt_tokens), 0).label("total_prompt_tokens"),
                func.coalesce(func.sum(LlmAuditLog.completion_tokens), 0).label(
                    "total_completion_tokens"
                ),
                total_tokens.label("total_tokens"),
                func.coalesce(func.sum(LlmAuditLog.cache_read_tokens), 0).label(
                    "total_cache_read_tokens"
                ),
                func.coalesce(func.sum(LlmAuditLog.cache_creation_tokens), 0).label(
                    "total_cache_creation_tokens"
                ),
                func.sum(LlmAuditLog.estimated_cost_usd).label("total_cost_usd"),
                func.coalesce(func.avg(LlmAuditLog.latency_ms), 0.0).label("avg_latency_ms"),
                func.sum(case((LlmAuditLog.status == "success", 1), else_=0)).label(
                    "success_count"
                ),
                func.sum(case((LlmAuditLog.status != "success", 1), else_=0)).label("error_count"),
            )
            .where(*filters)
            .group_by(LlmAuditLog.provider, LlmAuditLog.model)
            .order_by(total_tokens.desc())
        )
        return [dict(row) for row in (await self.db.execute(stmt)).mappings().all()]

    async def query_http(
        self,
        *,
        limit: int,
        offset: int,
        method: str | None = None,
        path: str | None = None,
        status_code: int | None = None,
        request_id: str | None = None,
    ) -> tuple[list[HttpLog], int]:
        """Return a page of HTTP logs (newest first) and the total count."""
        filters: list[ColumnElement[bool]] = []
        if method:
            filters.append(HttpLog.method == method)
        if path:
            filters.append(HttpLog.path.ilike(f"%{path}%"))
        if status_code:
            filters.append(HttpLog.status_code == status_code)
        if request_id:
            filters.append(HttpLog.request_id == request_id)

        stmt = (
            select(HttpLog)
            .where(*filters)
            .order_by(HttpLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        total = (
            await self.db.execute(select(func.count()).select_from(HttpLog).where(*filters))
        ).scalar_one()
        return rows, total

    async def query_errors(
        self,
        *,
        limit: int,
        offset: int,
        error_type: str | None = None,
    ) -> tuple[list[ErrorLog], int]:
        """Return a page of error logs (newest first) and the total count."""
        filters: list[ColumnElement[bool]] = []
        if error_type:
            filters.append(ErrorLog.error_type == error_type)

        stmt = (
            select(ErrorLog)
            .where(*filters)
            .order_by(ErrorLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        total = (
            await self.db.execute(select(func.count()).select_from(ErrorLog).where(*filters))
        ).scalar_one()
        return rows, total
