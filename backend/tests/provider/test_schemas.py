"""Validation tests for provider create/update schemas (security hardening)."""

import pytest
from pydantic import ValidationError
from src.provider.models import ProviderType
from src.provider.schemas import ProviderCreate, ProviderUpdate


def _create(**overrides):
    base = {
        "name": "Custom",
        "provider_type": ProviderType.CUSTOM,
        "base_url": "https://api.example.com",
        "api_key_env_var": "MYPROVIDER_API_KEY",
    }
    base.update(overrides)
    return ProviderCreate(**base)


def test_valid_custom_provider() -> None:
    p = _create()
    assert p.api_key_env_var == "MYPROVIDER_API_KEY"
    assert p.base_url == "https://api.example.com"


@pytest.mark.parametrize(
    "env_var",
    [
        "DATABASE_URL",  # not credential-shaped
        "ENCRYPTION_KEY",  # app secret (ends _KEY but denied by name)
        "AWS_SECRET_ACCESS_KEY",  # contains SECRET
        "DB_PASSWORD",  # contains PASSWORD
        "MY_PRIVATE_KEY",  # contains PRIVATE
        "PLAIN_NAME",  # no credential suffix
        "lowercase_api_key",  # wrong format
    ],
)
def test_rejects_sensitive_or_malformed_env_var(env_var: str) -> None:
    with pytest.raises(ValidationError):
        _create(api_key_env_var=env_var)


@pytest.mark.parametrize("env_var", ["OPENAI_API_KEY", "HF_TOKEN", "CUSTOM_KEY"])
def test_accepts_credential_shaped_env_var(env_var: str) -> None:
    assert _create(api_key_env_var=env_var).api_key_env_var == env_var


@pytest.mark.parametrize("url", ["file:///etc/passwd", "gopher://x", "ftp://x", "javascript:1"])
def test_rejects_non_http_base_url(url: str) -> None:
    with pytest.raises(ValidationError):
        _create(base_url=url)


def test_accepts_localhost_base_url() -> None:
    # Ollama / LM Studio on localhost is a first-class use case.
    assert _create(base_url="http://localhost:11434").base_url == "http://localhost:11434"


def test_update_applies_same_validation() -> None:
    with pytest.raises(ValidationError):
        ProviderUpdate(api_key_env_var="DATABASE_URL")
    with pytest.raises(ValidationError):
        ProviderUpdate(base_url="file:///etc/passwd")
    assert ProviderUpdate(api_key_env_var="OK_API_KEY").api_key_env_var == "OK_API_KEY"
