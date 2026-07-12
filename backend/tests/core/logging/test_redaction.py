"""Tests for sensitive-data redaction (recurses into dicts and lists)."""

from typing import Any

from src.core.logging.logger_config import redact_sensitive_data, redact_value


def test_redacts_top_level_secret() -> None:
    out = redact_sensitive_data({"api_key": "sk-1234567890abcdef", "model": "gpt"})
    assert out["api_key"] == "sk-1...cdef"
    assert out["model"] == "gpt"


def test_redacts_secret_nested_in_list() -> None:
    """Previously missed: a secret inside a list of dicts must still be masked."""
    out = redact_sensitive_data({"items": [{"api_key": "sk-abcdefghijkl"}, {"name": "ok"}]})
    items: list[dict[str, Any]] = out["items"]
    assert items[0]["api_key"] == "sk-a...ijkl"
    assert items[1]["name"] == "ok"


def test_redact_value_handles_list_payload() -> None:
    """LLM request payloads are lists — redact_value scrubs nested secrets."""
    payload = [
        {"role": "system", "content": "hello"},
        {"role": "user", "authorization": "Bearer verysecrettoken"},
    ]
    out = redact_value(payload)
    assert out[0]["content"] == "hello"
    assert out[1]["authorization"] != "Bearer verysecrettoken"


def test_short_secret_fully_masked() -> None:
    out = redact_sensitive_data({"token": "abc"})
    assert out["token"] == "***REDACTED***"
