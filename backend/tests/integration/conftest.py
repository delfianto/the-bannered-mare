"""Fixtures for provider integration tests.

These tests make REAL HTTP calls to LLM provider APIs.
They are skipped when the corresponding API key is not set in the environment.
"""

import os
from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool
from src.core.persistence.database import get_async_db_url
from src.core.persistence.enums import ProviderType
from src.provider.adapters.lmstudio import strip_v1_suffix
from src.provider.gateway import ProviderGateway

# Integration tests read provider keys from .env. The per-provider skip markers
# (has_*_key) evaluate os.environ at import time, so .env must be loaded before
# any test module is collected — this conftest is imported first, so load it here.
_ = load_dotenv()


def _pg_url() -> str | None:
    """Return DATABASE_URL only if it points at a real PostgreSQL instance."""
    url = os.environ.get("DATABASE_URL", "")
    return url if url.startswith("postgresql") else None


@pytest_asyncio.fixture
async def pg_async_session() -> AsyncGenerator[AsyncSession]:
    """Async session bound to the real Postgres container (DATABASE_URL).

    Rolls back at teardown so each test is isolated with no explicit cleanup —
    pgvector search sees uncommitted rows within the same transaction.
    """
    url = _pg_url()
    if not url:
        pytest.skip("DATABASE_URL not set to a PostgreSQL instance")

    engine = create_async_engine(get_async_db_url(url), poolclass=NullPool)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.rollback()
        await session.close()
        await engine.dispose()


@pytest.fixture
def pg_sync_session() -> Generator[Session]:
    """Sync session bound to the real Postgres container (DATABASE_URL)."""
    url = _pg_url()
    if not url:
        pytest.skip("DATABASE_URL not set to a PostgreSQL instance")

    engine = create_engine(url, poolclass=NullPool)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        engine.dispose()


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
    unsupported_params: list[str] | None = None,
) -> Any:
    """Create a mock ModelRegistry ORM object with parameters (identifier held for convenience)."""
    model = MagicMock()
    model.model_identifier = model_id
    model.parameters = model_params or {}
    model.model_family = MagicMock()
    model.model_family.parameters = family_params or {}
    # Must be a real list: the gateway strips family.unsupported_parameters, and a
    # bare MagicMock here would not be iterable.
    model.model_family.unsupported_parameters = unsupported_params or []
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


def _ollama_host() -> str:
    return os.environ.get("OLLAMA_HOST", "http://localhost:11434")


def _lmstudio_host() -> str:
    return os.environ.get("LMSTUDIO_HOST", "http://localhost:1234")


def _ollama_available() -> bool:
    """Check if Ollama is running and has at least one model."""
    import httpx

    host = _ollama_host()
    try:
        resp = httpx.get(f"{host}/api/tags", timeout=2.0)
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
    return ProviderGateway(provider, model, model.model_identifier)


@pytest.fixture
def anthropic_gateway() -> ProviderGateway:
    provider = _make_provider(
        ProviderType.ANTHROPIC, "https://api.anthropic.com/v1", os.environ["ANTHROPIC_API_KEY"]
    )
    model = _make_model(
        "claude-haiku-4-5-20251001", model_params={"max_tokens": 32, "temperature": 0}
    )
    return ProviderGateway(provider, model, model.model_identifier)


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
    return ProviderGateway(provider, model, model.model_identifier)


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
    return ProviderGateway(provider, model, model.model_identifier)


@pytest.fixture
def ollama_gateway() -> ProviderGateway:
    """Use the first available Ollama model."""
    import httpx

    host = _ollama_host()
    resp = httpx.get(f"{host}/api/tags", timeout=2.0)
    model_name = resp.json()["models"][0]["name"]

    provider = _make_provider(ProviderType.OLLAMA, host, "")
    model = _make_model(model_name, model_params={"max_tokens": 256, "temperature": 0})
    return ProviderGateway(provider, model, model.model_identifier)


def _lmstudio_available() -> bool:
    """Check if LM Studio is running and has at least one model."""
    import httpx

    host = _lmstudio_host()
    endpoint = f"{strip_v1_suffix(host)}/v1/models"
    try:
        resp = httpx.get(endpoint, timeout=2.0)
        models = resp.json().get("data", [])
        return len(models) > 0
    except Exception:
        return False


has_lmstudio = pytest.mark.skipif(
    not _lmstudio_available(), reason="LM Studio not running or no models available"
)


@pytest.fixture
def lmstudio_gateway() -> ProviderGateway:
    """Use the first available LM Studio model."""
    import httpx

    host = _lmstudio_host()
    endpoint = f"{strip_v1_suffix(host)}/v1/models"
    resp = httpx.get(endpoint, timeout=2.0)
    model_name = resp.json()["data"][0]["id"]

    provider = _make_provider(ProviderType.LMSTUDIO, host, "")
    # LM Studio serves whatever the user has loaded — often a reasoning model.
    # Give it enough budget to emit content after its reasoning tokens (a 32-token
    # cap gets fully consumed by reasoning, leaving empty content).
    model = _make_model(model_name, model_params={"max_tokens": 512, "temperature": 0})
    return ProviderGateway(provider, model, model.model_identifier)
