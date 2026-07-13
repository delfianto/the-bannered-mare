"""Read-side service for audit logs (used by the admin API)"""

from datetime import datetime

from src.audit.repository_async import AuditRepository
from src.audit.schemas import (
    ErrorLogPage,
    ErrorLogResponse,
    HttpLogPage,
    HttpLogResponse,
    LlmAuditLogPage,
    LlmAuditLogResponse,
    LlmStatsResponse,
    LlmUsageStat,
)


class AuditQueryService:
    """Queries audit-log tables and shapes them into response DTOs."""

    def __init__(self, repo: AuditRepository):
        self.repo = repo

    async def query_llm(
        self,
        *,
        limit: int,
        skip: int,
        chat_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        status: str | None = None,
    ) -> LlmAuditLogPage:
        """Return a page of LLM audit logs."""
        rows, total = await self.repo.query_llm(
            limit=limit, offset=skip, chat_id=chat_id, provider=provider, model=model, status=status
        )
        return LlmAuditLogPage(
            logs=[LlmAuditLogResponse.model_validate(r) for r in rows],
            total=total,
            limit=limit,
            skip=skip,
        )

    async def llm_stats(
        self, *, start: datetime | None = None, end: datetime | None = None
    ) -> LlmStatsResponse:
        """Return aggregated LLM usage stats per provider/model."""
        rows = await self.repo.llm_stats(start=start, end=end)
        stats = [
            LlmUsageStat(
                provider=r["provider"],
                model=r["model"],
                total_calls=r["total_calls"],
                total_prompt_tokens=r["total_prompt_tokens"],
                total_completion_tokens=r["total_completion_tokens"],
                total_tokens=r["total_tokens"],
                total_cache_read_tokens=r["total_cache_read_tokens"],
                total_cache_creation_tokens=r["total_cache_creation_tokens"],
                total_cost_usd=(
                    round(r["total_cost_usd"], 4) if r["total_cost_usd"] is not None else None
                ),
                avg_latency_ms=round(r["avg_latency_ms"], 2),
                success_count=r["success_count"],
                error_count=r["error_count"],
                success_rate=(
                    round(r["success_count"] / r["total_calls"] * 100, 2)
                    if r["total_calls"]
                    else 0.0
                ),
            )
            for r in rows
        ]
        return LlmStatsResponse(
            stats=stats,
            period={
                "start": start.isoformat() if start else None,
                "end": end.isoformat() if end else None,
            },
        )

    async def query_http(
        self,
        *,
        limit: int,
        skip: int,
        method: str | None = None,
        path: str | None = None,
        status_code: int | None = None,
        request_id: str | None = None,
    ) -> HttpLogPage:
        """Return a page of HTTP request logs."""
        rows, total = await self.repo.query_http(
            limit=limit,
            offset=skip,
            method=method,
            path=path,
            status_code=status_code,
            request_id=request_id,
        )
        return HttpLogPage(
            logs=[HttpLogResponse.model_validate(r) for r in rows],
            total=total,
            limit=limit,
            skip=skip,
        )

    async def query_errors(
        self, *, limit: int, skip: int, error_type: str | None = None
    ) -> ErrorLogPage:
        """Return a page of error logs."""
        rows, total = await self.repo.query_errors(limit=limit, offset=skip, error_type=error_type)
        return ErrorLogPage(
            logs=[ErrorLogResponse.model_validate(r) for r in rows],
            total=total,
            limit=limit,
            skip=skip,
        )
