"""Tests for the production secret-hardening validator on Settings."""

import pytest
from pydantic import ValidationError
from src.core.config import _PLACEHOLDER_ENCRYPTION_KEY, Settings

_SECURE = {"encryption_key": "a-real-secret", "cors_origins": ["https://app.example.com"]}


def test_development_allows_insecure_defaults() -> None:
    """The default environment keeps the convenient placeholder secrets."""
    settings = Settings(environment="development")
    assert settings.encryption_key == _PLACEHOLDER_ENCRYPTION_KEY
    assert settings.cors_origins == ["*"]


def test_production_rejects_placeholder_encryption_key() -> None:
    with pytest.raises(ValidationError, match="ENCRYPTION_KEY is still the placeholder"):
        Settings(environment="production", cors_origins=["https://app.example.com"])


def test_production_rejects_wildcard_cors() -> None:
    with pytest.raises(ValidationError, match=r"CORS_ORIGINS contains '\*'"):
        Settings(environment="production", encryption_key="a-real-secret")


def test_production_reports_all_problems_at_once() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(environment="production")
    message = str(exc_info.value)
    assert "ENCRYPTION_KEY is still the placeholder" in message
    assert "CORS_ORIGINS contains '*'" in message


def test_production_with_real_secrets_boots() -> None:
    settings = Settings(environment="production", **_SECURE)
    assert settings.environment == "production"
    assert settings.cors_origins == ["https://app.example.com"]
