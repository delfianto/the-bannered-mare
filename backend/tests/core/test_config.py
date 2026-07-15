"""Tests for the production hardening validator on Settings.

Every case passes the security-relevant fields (environment, cors_origins,
database_url) explicitly so the assertions never depend on ambient env / a
loaded backend/.env leaking in.
"""

import pytest
from pydantic import ValidationError
from src.core.config import _PLACEHOLDER_DATABASE_URL, Settings

# A DSN that is clearly not the shipped placeholder.
_REAL_DATABASE_URL = "postgresql+asyncpg://svc:s3cr3t@db.internal:5432/bannered_mare"
_EXPLICIT_ORIGINS = ["https://app.example.com"]


def test_development_allows_wildcard_cors() -> None:
    """The default environment keeps the convenient wildcard CORS."""
    settings = Settings(environment="development")
    assert settings.cors_origins == ["*"]


def test_production_rejects_wildcard_cors() -> None:
    with pytest.raises(ValidationError, match=r"CORS_ORIGINS contains '\*'"):
        Settings(environment="production")


def test_production_with_explicit_origins_boots() -> None:
    settings = Settings(
        environment="production",
        cors_origins=_EXPLICIT_ORIGINS,
        database_url=_REAL_DATABASE_URL,
    )
    assert settings.environment == "production"
    assert settings.cors_origins == _EXPLICIT_ORIGINS


def test_production_rejects_placeholder_database_url() -> None:
    """A prod boot against the shipped placeholder DSN must fail loudly, not silently."""
    with pytest.raises(ValidationError, match=r"DATABASE_URL is the shipped placeholder"):
        Settings(
            environment="production",
            cors_origins=_EXPLICIT_ORIGINS,
            database_url=_PLACEHOLDER_DATABASE_URL,
        )


def test_production_with_real_database_url_boots() -> None:
    settings = Settings(
        environment="production",
        cors_origins=_EXPLICIT_ORIGINS,
        database_url=_REAL_DATABASE_URL,
    )
    assert settings.database_url == _REAL_DATABASE_URL


def test_development_allows_placeholder_database_url() -> None:
    """The shipped placeholder DSN is fine outside production (dev default still works)."""
    settings = Settings(
        environment="development",
        database_url=_PLACEHOLDER_DATABASE_URL,
    )
    assert settings.database_url == _PLACEHOLDER_DATABASE_URL
