"""Pytest configuration and fixtures"""

import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from typing import TYPE_CHECKING

# Disable the fire-and-forget audit writer in tests (its own session is not the test DB)
os.environ.setdefault("LOGGING__AUDIT_ENABLED", "false")

import pytest  # noqa: E402
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from src.core.persistence import Base, get_async_db, get_db
from src.main import app

if TYPE_CHECKING:
    from src.character import Character  # noqa: F401
    from src.chat_session.models import Chat  # noqa: F401
    from src.model import Model  # noqa: F401
    from src.model_family import ModelFamily  # noqa: F401
    from src.persona import Persona  # noqa: F401
    from src.provider import Provider  # noqa: F401


def _import_all_models():
    """Ensure all ORM models are registered with Base.metadata."""
    import src.audit.models  # noqa: F401 # pyright: ignore[reportUnusedImport]
    import src.character.models  # noqa: F401 # pyright: ignore[reportUnusedImport]
    import src.chat_message.models  # noqa: F401 # pyright: ignore[reportUnusedImport]
    import src.chat_session.models  # noqa: F401 # pyright: ignore[reportUnusedImport]
    import src.model.models  # noqa: F401 # pyright: ignore[reportUnusedImport]
    import src.model_family.models  # noqa: F401 # pyright: ignore[reportUnusedImport]
    import src.persona.models  # noqa: F401 # pyright: ignore[reportUnusedImport]
    import src.preset.models  # noqa: F401 # pyright: ignore[reportUnusedImport]
    import src.profile.models  # noqa: F401 # pyright: ignore[reportUnusedImport]
    import src.prompt_fragment.models  # noqa: F401 # pyright: ignore[reportUnusedImport]
    import src.prompt_template.models  # noqa: F401 # pyright: ignore[reportUnusedImport]
    import src.provider.models  # noqa: F401 # pyright: ignore[reportUnusedImport]
    import src.rag.models  # noqa: F401 # pyright: ignore[reportUnusedImport]


def _delete_all_rows(engine: Engine):
    """Delete all rows from all tables (respecting FK ordering)."""
    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


async def _async_delete_all_rows(engine: AsyncEngine):
    """Async version — delete all rows from all tables."""
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


# ---------------------------------------------------------------------------
# Session-scoped engines — create schema ONCE for entire test run
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine]:
    """Create an in-memory SQLite engine (sync). Schema created once."""
    _import_all_models()
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def async_db_engine() -> Generator[AsyncEngine]:
    """Create an in-memory SQLite engine (async). Schema created once."""
    _import_all_models()
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    loop = asyncio.new_event_loop()
    loop.run_until_complete(_async_create_tables(engine))
    yield engine
    loop.run_until_complete(engine.dispose())
    loop.close()


async def _async_create_tables(engine: AsyncEngine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ---------------------------------------------------------------------------
# Function-scoped sessions — clean between tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def db_session(db_engine: Engine) -> Generator[Session]:
    """Create a new database session. Cleans all rows after the test."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        _delete_all_rows(db_engine)


@pytest_asyncio.fixture(scope="function")
async def async_db_session(async_db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    """Create a new async database session. Cleans all rows after the test."""
    AsyncTestingSessionLocal = async_sessionmaker(
        bind=async_db_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    session = AsyncTestingSessionLocal()

    async def override_get_async_db():
        yield session

    app.dependency_overrides[get_async_db] = override_get_async_db

    try:
        yield session
    finally:
        await session.rollback()
        await session.close()
        await _async_delete_all_rows(async_db_engine)
        app.dependency_overrides.pop(get_async_db, None)


# ---------------------------------------------------------------------------
# Convenience aliases and test client
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def db(db_session: Session) -> Session:
    """Alias for db_session for convenience"""
    return db_session


@pytest.fixture(scope="function")
def client(db_session: Session, async_db_engine: AsyncEngine) -> Generator[TestClient]:
    """Create a test client with both sync and async database sessions"""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    async def override_get_async_db():
        AsyncTestSessionLocal = async_sessionmaker(
            bind=async_db_engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
        async with AsyncTestSessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_async_db] = override_get_async_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Sample data fixtures (function-scoped)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def sample_provider(db: Session) -> Provider:
    """Create a sample provider for testing"""
    from src.provider import Provider, ProviderType

    provider = Provider(name="OpenAI", provider_type=ProviderType.OPENAI)
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


@pytest.fixture(scope="function")
def sample_family(db: Session) -> ModelFamily:
    """Create a sample model family for testing"""
    from src.model_family import ModelFamily

    family = ModelFamily(
        name="GPT",
        family_identifier="test.gpt",
        provider_types=["openai"],
        parameters={
            "temperature": {"type": "float", "default": 1.0, "min_value": 0.0, "max_value": 2.0},
            "max_tokens": {"type": "int", "default": 2048, "min_value": 1},
        },
    )
    db.add(family)
    db.commit()
    db.refresh(family)
    return family


@pytest.fixture(scope="function")
def sample_model(db: Session, sample_provider: Provider, sample_family: ModelFamily) -> Model:
    """Create a sample model for testing"""
    from src.model import Model

    model = Model(
        name="GPT-4",
        provider_id=sample_provider.id,
        model_identifier="gpt-4",
        model_family_id=sample_family.id,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@pytest.fixture(scope="function")
def sample_character(db: Session) -> Character:
    """Create a sample character for testing"""
    from src.character import Character

    character = Character(name="Alice", description="Test character")
    db.add(character)
    db.commit()
    db.refresh(character)
    return character


@pytest.fixture(scope="function")
def sample_persona(db: Session) -> Persona:
    """Create a sample persona for testing"""
    from src.persona import Persona

    persona = Persona(name="User", description="Test persona")
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return persona


@pytest.fixture(scope="function")
def seeded_providers(db: Session) -> None:
    """Seed default providers"""
    from src.fixtures.seed_providers import seed_providers
    from src.provider.repository import ProviderRepository

    repo = ProviderRepository(db)
    seed_providers(repo)


@pytest.fixture(scope="function")
def test_chat_id(db: Session, sample_character: Character, sample_model: Model) -> str:
    """Create a chat and return its ID"""
    from src.chat_session.models import Chat

    chat = Chat(character_id=sample_character.id, model_id=sample_model.id)
    db.add(chat)
    db.commit()
    return chat.id


@pytest.fixture(scope="function")
def test_api_key_env(monkeypatch: pytest.MonkeyPatch):
    """Mock API key environment variable"""
    monkeypatch.setenv("OPENAI_API_KEY", "test_key")


# ASYNC FIXTURES
@pytest_asyncio.fixture(scope="function")
async def async_sample_provider(async_db_session: AsyncSession) -> Provider:
    """Create a sample provider for async testing"""
    from src.provider import Provider, ProviderType

    provider = Provider(name="OpenAI", provider_type=ProviderType.OPENAI)
    async_db_session.add(provider)
    await async_db_session.commit()
    await async_db_session.refresh(provider)
    return provider


@pytest_asyncio.fixture(scope="function")
async def async_sample_family(async_db_session: AsyncSession) -> ModelFamily:
    """Create a sample model family for async testing"""
    from src.model_family import ModelFamily

    family = ModelFamily(
        name="GPT",
        family_identifier="test.gpt",
        provider_types=["openai"],
        parameters={
            "temperature": {"type": "float", "default": 1.0, "min_value": 0.0, "max_value": 2.0},
            "max_tokens": {"type": "int", "default": 2048, "min_value": 1},
        },
    )
    async_db_session.add(family)
    await async_db_session.commit()
    await async_db_session.refresh(family)
    return family


@pytest_asyncio.fixture(scope="function")
async def async_sample_model(
    async_db_session: AsyncSession,
    async_sample_provider: Provider,
    async_sample_family: ModelFamily,
) -> Model:
    """Create a sample model for async testing"""
    from src.model import Model

    model = Model(
        name="GPT-4",
        provider_id=async_sample_provider.id,
        model_identifier="gpt-4",
        model_family_id=async_sample_family.id,
    )
    async_db_session.add(model)
    await async_db_session.commit()
    await async_db_session.refresh(model)
    return model


@pytest_asyncio.fixture(scope="function")
async def async_sample_character(async_db_session: AsyncSession) -> Character:
    """Create a sample character for async testing"""
    from src.character import Character

    character = Character(name="Alice", description="Test character")
    async_db_session.add(character)
    await async_db_session.commit()
    await async_db_session.refresh(character)
    return character


@pytest_asyncio.fixture(scope="function")
async def async_test_chat_id(
    async_db_session: AsyncSession,
    async_sample_character: Character,
    async_sample_model: Model,
) -> str:
    """Create a chat and return its ID for async testing"""
    from src.chat_session.models import Chat

    chat = Chat(character_id=async_sample_character.id, model_id=async_sample_model.id)
    async_db_session.add(chat)
    await async_db_session.commit()
    return chat.id
