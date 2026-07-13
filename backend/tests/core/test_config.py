"""Tests for the production CORS-hardening validator on Settings."""

import pytest
from pydantic import ValidationError
from src.core.config import Settings


def test_development_allows_wildcard_cors() -> None:
    """The default environment keeps the convenient wildcard CORS."""
    settings = Settings(environment="development")
    assert settings.cors_origins == ["*"]


def test_production_rejects_wildcard_cors() -> None:
    with pytest.raises(ValidationError, match=r"CORS_ORIGINS contains '\*'"):
        Settings(environment="production")


def test_production_with_explicit_origins_boots() -> None:
    settings = Settings(environment="production", cors_origins=["https://app.example.com"])
    assert settings.environment == "production"
    assert settings.cors_origins == ["https://app.example.com"]
