"""Isolated eager-load tests for ``AsyncChatRepository.find_by_id_with_relations``.

The async session cannot lazy-load, so every relation the prompt builder and
gateway walk must be eager-loaded up front or it raises ``MissingGreenlet`` at
access time. ``test_service`` pins the *task*-model chain; these pin the *main*
model chain plus character/persona, so a dropped ``joinedload`` in the option set
is caught at the repository layer rather than as a runtime "cannot reach the
model" failure.
"""

from typing import Any

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession
from src.chat_session.models import Chat
from src.chat_session.repository_async import AsyncChatRepository
from src.provider import ProviderType


@pytest.mark.asyncio
async def test_find_by_id_with_relations_eager_loads_main_chains(
    async_db_session: AsyncSession,
    async_sample_character: Any,
    async_sample_model: Any,
):
    """character, model -> active_route -> provider, model -> model_family, and a
    persona all come back loaded from a single query."""
    from src.persona import Persona

    persona = Persona(name="Traveler", description="Test persona")
    async_db_session.add(persona)
    await async_db_session.flush()

    chat = Chat(
        character_id=async_sample_character.id,
        model_id=async_sample_model.id,
        persona_id=persona.id,
    )
    async_db_session.add(chat)
    await async_db_session.commit()

    # Clear the identity map so the query's eager-load options — not already-loaded
    # in-session instances — decide what is populated.
    async_db_session.expunge_all()

    repo = AsyncChatRepository(async_db_session)
    loaded = await repo.find_by_id_with_relations(chat.id)
    assert loaded is not None

    # Top-level relations are loaded (not pending a lazy fetch).
    for relation in ("character", "model", "persona", "task_model", "template", "preset"):
        assert relation not in inspect(loaded).unloaded

    # Accessing the deep chains would raise MissingGreenlet if any link in the
    # option set were missing — so these assertions are the real regression guard.
    assert loaded.character.name == "Alice"
    assert loaded.persona is not None and loaded.persona.name == "Traveler"

    assert loaded.model is not None
    assert loaded.model.model_family.family_identifier == "test.gpt"
    route = loaded.model.active_route
    assert route is not None
    assert route.provider.provider_type == ProviderType.OPENAI


@pytest.mark.asyncio
async def test_find_by_id_with_relations_missing_returns_none(
    async_db_session: AsyncSession,
):
    """An unknown chat id resolves to ``None`` rather than raising."""
    repo = AsyncChatRepository(async_db_session)
    assert await repo.find_by_id_with_relations("nope") is None
