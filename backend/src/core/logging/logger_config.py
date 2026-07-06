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


def redact_sensitive_data(data: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive information from log data"""
    if not settings.logging.redact_api_keys:
        return data

    sensitive_keys = [
        "api_key",
        "apikey",
        "authorization",
        "password",
        "secret",
        "token",
        "x-api-key",
    ]

    redacted = data.copy()
    for key, value in redacted.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            if isinstance(value, str) and len(value) > 8:
                redacted[key] = f"{value[:4]}...{value[-4:]}"
            else:
                redacted[key] = "***REDACTED***"
        elif isinstance(value, dict):
            redacted[key] = redact_sensitive_data(cast(Any, value))

    return redacted
