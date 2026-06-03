"""Audit/logging ORM models (LLM calls, HTTP requests, errors)."""

from __future__ import annotations

from typing import Any, final

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.persistence.models._base import BaseModel, JsonDict


@final
class LlmAuditLog(BaseModel):
    """Audit record for a single LLM completion call (request + response payloads)"""

    __tablename__ = "llm_audit_logs"
    __table_args__ = (Index("ix_llm_audit_logs_chat_created", "chat_id", "created_at"),)

    chat_id: Mapped[str | None] = mapped_column(
        String(12),
        ForeignKey("chats.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Chat this call belongs to (null if the chat was deleted)",
    )
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Provider type (e.g. openai, anthropic)"
    )
    model: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Model identifier sent to the provider"
    )
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="success or an error classification"
    )
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_payload: Mapped[list[dict[str, Any]]] = mapped_column(
        JsonDict, nullable=False, comment="Raw request messages sent to the provider"
    )
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JsonDict,
        nullable=True,
        comment="Raw response (content, reasoning, finish_reason, usage)",
    )


@final
class HttpLog(BaseModel):
    """Audit record for a single HTTP request/response handled by the API"""

    __tablename__ = "http_logs"
    __table_args__ = (Index("ix_http_logs_created", "created_at"),)

    request_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(String(2048), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    client_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_body: Mapped[dict[str, Any] | None] = mapped_column(JsonDict, nullable=True)
    response_body: Mapped[dict[str, Any] | None] = mapped_column(JsonDict, nullable=True)


@final
class ErrorLog(BaseModel):
    """Audit record for an unhandled application error"""

    __tablename__ = "error_logs"
    __table_args__ = (Index("ix_error_logs_type_created", "error_type", "created_at"),)

    error_type: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    stack_trace: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[dict[str, Any]] = mapped_column(JsonDict, nullable=False, default=dict)
