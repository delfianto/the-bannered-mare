"""Structured logging configuration using structlog"""

import logging
import sys
from typing import Any, cast

import structlog

from src.core.config import settings


def configure_structlog():
    """Configure structlog for the application"""

    # Determine processors based on format
    if settings.logging.format == "json":
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Console format for development
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.logging.level.upper()),
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name)


_SENSITIVE_EXACT = frozenset(
    {
        "token",
        "api_key",
        "apikey",
        "authorization",
        "password",
        "secret",
        "x-api-key",
    }
)
_SENSITIVE_SUFFIXES = ("_token", "-token")
_USAGE_SUFFIX = "_tokens"


def _is_sensitive_key(key: str) -> bool:
    """Match auth-bearing keys without catching usage counters.

    The old substring rule (``"token" in key``) matched ``input_tokens``,
    ``cache_read_tokens``, etc., redacting the audit trail's usage data.
    Exact-set + ``_token``/``-token`` suffix matching avoids that, and the
    ``_tokens`` plural is explicitly excluded as a safety net.
    """
    k = key.lower()
    if k.endswith(_USAGE_SUFFIX):
        return False
    if k in _SENSITIVE_EXACT:
        return True
    return any(k.endswith(suffix) for suffix in _SENSITIVE_SUFFIXES)


def _redact_field(key: str, value: Any) -> Any:
    """Redact a value whose key looks sensitive; else recurse into it."""
    if _is_sensitive_key(key):
        if isinstance(value, str) and len(value) > 8:
            return f"{value[:4]}...{value[-4:]}"
        return "***REDACTED***"
    return _redact_value(value)


def _redact_value(value: Any) -> Any:
    """Recurse through dicts AND lists so secrets nested in either are masked."""
    if isinstance(value, dict):
        return {k: _redact_field(k, v) for k, v in cast(dict[str, Any], value).items()}
    if isinstance(value, list):
        return [_redact_value(v) for v in cast(list[Any], value)]
    return value


def redact_value(value: Any) -> Any:
    """Recursively redact secrets in an arbitrary JSON-ish value (dict / list / scalar)."""
    if not settings.logging.redact_api_keys:
        return value
    return _redact_value(value)


def redact_sensitive_data(data: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive information from a log-data mapping (recurses into lists)."""
    if not settings.logging.redact_api_keys:
        return data
    return {k: _redact_field(k, v) for k, v in data.items()}
