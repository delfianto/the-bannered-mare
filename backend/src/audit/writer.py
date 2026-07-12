"""Fire-and-forget audit writer backed by PostgreSQL.

Each write opens its own AsyncSession (decoupled from the request transaction)
and swallows all errors — audit logging must never break a request or roll back
the chat transaction.
"""

from typing import Any

from src.audit.repository_async import AuditRepository
from src.core.config import settings
from src.core.logging.logger_config import get_logger, redact_sensitive_data, redact_value
from src.core.persistence.database import AsyncSessionLocal
from src.core.persistence.models import ErrorLog, HttpLog, LlmAuditLog

logger = get_logger(__name__)


class AuditWriter:
    """Writes audit records to Postgres on a dedicated, best-effort session."""

    async def log_http_request(
        self,
        *,
        request_id: str,
        method: str,
        path: str,
        status_code: int,
        latency_ms: float,
        client_ip: str | None = None,
        user_agent: str | None = None,
        request_body: dict[str, Any] | None = None,
        response_body: dict[str, Any] | None = None,
    ) -> None:
        """Record one HTTP request/response."""
        if not settings.logging.audit_enabled or not settings.logging.log_http_requests:
            return

        entry = HttpLog(
            request_id=request_id,
            method=method,
            path=path,
            status_code=status_code,
            latency_ms=latency_ms,
            client_ip=client_ip,
            user_agent=user_agent,
            request_body=(
                redact_sensitive_data(request_body)
                if request_body and settings.logging.log_request_body
                else None
            ),
            response_body=(
                redact_sensitive_data(response_body)
                if response_body and settings.logging.log_response_body
                else None
            ),
        )
        await self._write(entry, kind="http_logs")

    async def log_llm_call(
        self,
        *,
        chat_id: str | None,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        latency_ms: float,
        status: str,
        estimated_cost_usd: float | None = None,
        error_message: str | None = None,
        request_payload: list[dict[str, Any]] | None = None,
        response_payload: dict[str, Any] | None = None,
    ) -> None:
        """Record one LLM completion call (request + response payloads)."""
        if not settings.logging.audit_enabled or not settings.logging.log_llm_calls:
            return

        entry = LlmAuditLog(
            chat_id=chat_id,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            status=status,
            estimated_cost_usd=estimated_cost_usd,
            error_message=error_message,
            request_payload=redact_value(request_payload or []),
            response_payload=redact_value(response_payload),
        )
        await self._write(entry, kind="llm_audit_logs")

    async def log_error(
        self,
        *,
        error_type: str,
        message: str,
        stack_trace: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Record one unhandled application error."""
        if not settings.logging.audit_enabled or not settings.logging.log_errors:
            return

        entry = ErrorLog(
            error_type=error_type,
            message=message,
            stack_trace=stack_trace,
            context=redact_sensitive_data(context) if context else {},
        )
        await self._write(entry, kind="error_logs")

    async def _write(self, entry: LlmAuditLog | HttpLog | ErrorLog, *, kind: str) -> None:
        """Persist one record on a dedicated session; never raise."""
        try:
            async with AsyncSessionLocal() as db:
                await AuditRepository(db).add(entry)
                await db.commit()
        except Exception as e:
            logger.error("audit_write_failed", collection=kind, error=str(e))


# Global writer instance
audit_logger = AuditWriter()
