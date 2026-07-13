"""Pydantic DTOs for audit-log read endpoints"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class LlmAuditLogResponse(BaseModel):
    """A single LLM audit record"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    chat_id: str | None
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    latency_ms: float
    status: str
    estimated_cost_usd: float | None
    error_message: str | None
    request_payload: list[dict[str, Any]]
    response_payload: dict[str, Any] | None


class HttpLogResponse(BaseModel):
    """A single HTTP request audit record"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    request_id: str
    method: str
    path: str
    status_code: int
    latency_ms: float
    client_ip: str | None
    user_agent: str | None
    request_body: dict[str, Any] | None
    response_body: dict[str, Any] | None


class ErrorLogResponse(BaseModel):
    """A single error audit record"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    error_type: str
    message: str
    stack_trace: str | None
    context: dict[str, Any]


class LlmUsageStat(BaseModel):
    """Aggregated usage stats for one provider/model pair"""

    provider: str
    model: str
    total_calls: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_cache_read_tokens: int
    total_cache_creation_tokens: int
    total_cost_usd: float | None
    avg_latency_ms: float
    success_count: int
    error_count: int
    success_rate: float


class StatsPeriod(BaseModel):
    """The time window a stats query covers (ISO-8601 bounds; null = open-ended)."""

    start: str | None = None
    end: str | None = None


class LlmStatsResponse(BaseModel):
    """LLM usage stats over an optional time window"""

    stats: list[LlmUsageStat]
    period: StatsPeriod
