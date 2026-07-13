"""LLM-call audit recording for the chat message flow.

Stateless helpers extracted from ChatMessageService: they record one audit row
per provider call (success, non-usable outcome, or error) and classify the
completion. Kept as plain functions — they hold no service state, only the
gateway + call metadata passed in — so both the blocking and streaming paths call
them the same way.
"""

import time
from typing import Any

from src.audit.writer import audit_logger
from src.core.exceptions import (
    ProviderAuthError,
    ProviderException,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from src.core.logging.logger_config import get_logger
from src.provider.adapters.base import TokenUsage
from src.provider.completion_outcome import CompletionOutcome, classify_completion
from src.provider.gateway import ProviderGateway

logger = get_logger(__name__)


def classify_error(exc: Exception) -> str:
    """Map a provider exception to an audit/stream status code."""
    if isinstance(exc, ProviderRateLimitError):
        return "rate_limit"
    if isinstance(exc, ProviderAuthError):
        return "auth_error"
    if isinstance(exc, ProviderTimeoutError):
        return "timeout"
    if isinstance(exc, ProviderException):
        return "provider_error"
    return "internal_error"


async def record_llm_audit(
    *,
    gateway: ProviderGateway,
    api_messages: list[dict[str, Any]],
    chat_id: str,
    latency_ms: float,
    error: Exception | None = None,
    content: str | None = None,
    reasoning: str | None = None,
    finish_reason: str | None = None,
    usage: TokenUsage | None = None,
    raw: dict[str, Any] | None = None,
    status_override: str | None = None,
) -> None:
    """Record one LLM-call audit row (fire-and-forget; never raises).

    ``status_override`` records a non-error but non-``success`` outcome
    (filtered / empty / truncated) so LLM Logs no longer files these as
    successes.
    """
    try:
        provider = gateway.provider.provider_type.value
        model = gateway.active_identifier
        if error is not None:
            await audit_logger.log_llm_call(
                chat_id=chat_id,
                provider=provider,
                model=model,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                latency_ms=latency_ms,
                status=classify_error(error),
                error_message=str(error),
                request_payload=api_messages,
                response_payload=None,
            )
            return

        usage_dict = None
        in_tok = out_tok = tot_tok = 0
        cache_read = cache_creation = 0
        if usage is not None:
            in_tok, out_tok, tot_tok = (
                usage.input_tokens,
                usage.output_tokens,
                usage.total_tokens,
            )
            cache_read = usage.cache_read_tokens
            cache_creation = usage.cache_creation_tokens
            usage_dict = {
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "total_tokens": usage.total_tokens,
                "cache_read_tokens": usage.cache_read_tokens,
                "cache_creation_tokens": usage.cache_creation_tokens,
            }
        response_payload: dict[str, Any] = {
            "content": content,
            "reasoning": reasoning,
            "finish_reason": finish_reason,
            "usage": usage_dict,
        }
        if raw is not None:
            response_payload["raw"] = raw

        await audit_logger.log_llm_call(
            chat_id=chat_id,
            provider=provider,
            model=model,
            prompt_tokens=in_tok,
            completion_tokens=out_tok,
            total_tokens=tot_tok,
            latency_ms=latency_ms,
            status=status_override or "success",
            request_payload=api_messages,
            response_payload=response_payload,
            cache_read_tokens=cache_read,
            cache_creation_tokens=cache_creation,
        )
    except Exception:
        logger.warning("llm_audit_capture_failed", exc_info=True)


async def classify_and_audit(
    *,
    gateway: ProviderGateway,
    api_messages: list[dict[str, Any]],
    chat_id: str,
    start: float,
    content: str | None,
    reasoning: str | None,
    finish_reason: str | None,
    usage: TokenUsage | None,
    raw: dict[str, Any] | None = None,
) -> CompletionOutcome:
    """Classify the completion, record the audit (status = the outcome), and warn
    on a non-usable result. The caller decides how to surface it (raise vs stream
    error event)."""
    outcome = classify_completion(content, reasoning, finish_reason)
    await record_llm_audit(
        gateway=gateway,
        api_messages=api_messages,
        chat_id=chat_id,
        latency_ms=(time.perf_counter() - start) * 1000,
        content=content,
        reasoning=reasoning,
        finish_reason=finish_reason,
        usage=usage,
        raw=raw,
        status_override=None if outcome == CompletionOutcome.USABLE else outcome.value,
    )
    if outcome != CompletionOutcome.USABLE:
        logger.warning(
            "non_usable_completion",
            chat_id=chat_id,
            outcome=outcome.value,
            finish_reason=finish_reason,
        )
    return outcome


async def audit_error(
    *,
    gateway: ProviderGateway,
    api_messages: list[dict[str, Any]],
    chat_id: str,
    start: float,
    error: Exception,
) -> None:
    """Record a failed LLM call (exception path)."""
    await record_llm_audit(
        gateway=gateway,
        api_messages=api_messages,
        chat_id=chat_id,
        latency_ms=(time.perf_counter() - start) * 1000,
        error=error,
    )
