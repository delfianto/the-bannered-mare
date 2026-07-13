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


def test_usage_counters_survive_redaction() -> None:
    """``input_tokens`` / ``cache_read_tokens`` are usage counters, not secrets —
    the old substring rule (``"token" in key``) masked them, blinding the audit
    trail's usage data."""
    out = redact_sensitive_data(
        {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_read_tokens": 80,
            "cache_creation_tokens": 20,
            "total_tokens": 150,
        }
    )
    assert out["input_tokens"] == 100
    assert out["output_tokens"] == 50
    assert out["cache_read_tokens"] == 80
    assert out["cache_creation_tokens"] == 20
    assert out["total_tokens"] == 150


def test_access_token_still_redacted() -> None:
    """``_token`` suffix (singular) is an auth token — must still be masked."""
    out = redact_sensitive_data({"access_token": "sk-1234567890abcdef"})
    assert out["access_token"] == "sk-1...cdef"


def test_hyphenated_token_still_redacted() -> None:
    """``-token`` suffix is also an auth token."""
    out = redact_sensitive_data({"auth-token": "sk-1234567890abcdef"})
    assert out["auth-token"] == "sk-1...cdef"


def test_authorization_still_redacted() -> None:
    out = redact_sensitive_data({"Authorization": "Bearer verysecret"})
    assert out["Authorization"] != "Bearer verysecret"


def test_x_api_key_still_redacted() -> None:
    out = redact_sensitive_data({"x-api-key": "sk-1234567890abcdef"})
    assert out["x-api-key"] == "sk-1...cdef"


def test_usage_nested_in_response_payload_survives() -> None:
    """The LLM audit response_payload.usage.* must survive redaction — this is
    where the cache hit/miss counts live."""
    out = redact_value(
        {
            "usage": {
                "input_tokens": 100,
                "cache_read_tokens": 80,
                "cache_creation_tokens": 20,
                "output_tokens": 50,
            }
        }
    )
    usage = out["usage"]
    assert usage["input_tokens"] == 100
    assert usage["cache_read_tokens"] == 80
    assert usage["cache_creation_tokens"] == 20
