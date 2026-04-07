"""Fixtures for provider integration tests.

These tests make REAL HTTP calls to LLM provider APIs.
They are skipped when the corresponding API key is not set in the environment.
"""

import os
from typing import Any
from unittest.mock import MagicMock

import pytest
from src.core.persistence.enums import ProviderType
from src.provider.gateway import ProviderGateway


def _make_provider(provider_type: ProviderType, base_url: str, api_key: str) -> Any:
    """Create a mock Provider ORM object with real connection settings."""
    provider = MagicMock()
    provider.provider_type = provider_type
    provider.get_api_key.return_value = api_key
    provider.get_base_url.return_value = base_url
    provider.has_api_key.return_value = True
    provider.name = provider_type.value
    return provider


def _make_model(
    model_id: str,
    family_params: dict[str, Any] | None = None,
    model_params: dict[str, Any] | None = None,
) -> Any:
    """Create a mock Model ORM object with parameters."""
    model = MagicMock()
    model.model_identifier = model_id
    model.use_openrouter = False
    model.parameters = model_params or {}
    model.model_family = MagicMock()
    model.model_family.parameters = family_params or {}
    return model


# ---------------------------------------------------------------------------
# Skip conditions
# ---------------------------------------------------------------------------

has_openai_key = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set"
)
has_anthropic_key = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set"
)
has_google_key = pytest.mark.skipif(
    not os.environ.get("GOOGLE_API_KEY"), reason="GOOGLE_API_KEY not set"
)
has_openrouter_key = pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)


def _ollama_available() -> bool:
    """Check if Ollama is running and has at least one model."""
    import httpx

    try:
        resp = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        models = resp.json().get("models", [])
        return len(models) > 0
    except Exception:
        return False


has_ollama = pytest.mark.skipif(
    not _ollama_available(), reason="Ollama not running or no models available"
)


# ---------------------------------------------------------------------------
# Gateway fixtures — one per provider
# ---------------------------------------------------------------------------

SIMPLE_MESSAGES = [
    {"role": "user", "content": "Reply with exactly one word: hello"},
]


@pytest.fixture
def openai_gateway() -> ProviderGateway:
    provider = _make_provider(
        ProviderType.OPENAI, "https://api.openai.com/v1", os.environ["OPENAI_API_KEY"]
    )
    model = _make_model("gpt-4o-mini", model_params={"max_tokens": 32, "temperature": 0})
    return ProviderGateway(provider, model)


@pytest.fixture
def anthropic_gateway() -> ProviderGateway:
    provider = _make_provider(
        ProviderType.ANTHROPIC, "https://api.anthropic.com/v1", os.environ["ANTHROPIC_API_KEY"]
    )
    model = _make_model(
        "claude-haiku-4-5-20251001", model_params={"max_tokens": 32, "temperature": 0}
    )
    return ProviderGateway(provider, model)


@pytest.fixture
def gemini_gateway() -> ProviderGateway:
    provider = _make_provider(
        ProviderType.GOOGLE,
        "https://generativelanguage.googleapis.com",
        os.environ["GOOGLE_API_KEY"],
    )
    model = _make_model(
        "gemini-2.5-flash",
        model_params={"max_output_tokens": 32, "temperature": 0},
    )
    return ProviderGateway(provider, model)


@pytest.fixture
def openrouter_gateway() -> ProviderGateway:
    provider = _make_provider(
        ProviderType.OPENROUTER,
        "https://openrouter.ai/api/v1",
        os.environ["OPENROUTER_API_KEY"],
    )
    model = _make_model(
        "nvidia/nemotron-3-nano-30b-a3b:free",
        model_params={"max_tokens": 256, "temperature": 0},
    )
    return ProviderGateway(provider, model)


@pytest.fixture
def ollama_gateway() -> ProviderGateway:
    """Use the first available Ollama model."""
    import httpx

    resp = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
    model_name = resp.json()["models"][0]["name"]

    provider = _make_provider(ProviderType.OLLAMA, "http://localhost:11434", "")
    model = _make_model(model_name, model_params={"max_tokens": 256, "temperature": 0})
    return ProviderGateway(provider, model)
