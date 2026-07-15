"""Tests for chat message router.

HTTP-level coverage that drives the router through the ASGI app (httpx
``AsyncClient`` over ``ASGITransport``), reusing the async fixtures. The LLM
gateway is mocked exactly as the service/streaming tests do — ``Provider.has_api_key``
is forced and ``gateway_factory.ProviderGateway`` is swapped for an ``AsyncMock`` —
so blocking sends, suggestions, and titles never reach a real provider.

Every write goes through the ASGI request (which shares the overridden async test
session and commits there), and the sync ``get_db`` override used on the send path
is read-only (prompt-template + lore lookups), so neither contends with the async
writer on the shared single-writer SQLite file.
"""

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from src.chat_message.models import Message, MessageRole
from src.chat_session.models import Chat
from src.core.persistence import get_db
from src.core.persistence.models import MessageAlternative
from src.main import app
from src.provider import Provider
from src.provider.adapters import CompletionResponse, TokenUsage


@asynccontextmanager
async def _asgi_client() -> AsyncIterator[AsyncClient]:
    """An HTTP client bound to the ASGI app (shares the overridden test sessions)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@contextmanager
def _mock_provider_gateway(
    *, response: CompletionResponse | None = None, error: Exception | None = None
) -> Iterator[AsyncMock]:
    """Swap the provider gateway so completions never reach a real provider.

    Mirrors the service/streaming mocking: force ``has_api_key`` and replace
    ``ProviderGateway`` (used by both the main and task gateway factories) with an
    ``AsyncMock`` whose ``chat_completion`` returns ``response`` or raises ``error``.
    """
    with (
        patch.object(Provider, "has_api_key", return_value=True),
        patch("src.chat_message.gateway_factory.ProviderGateway") as gateway_cls,
    ):
        gateway = AsyncMock()
        if error is not None:
            gateway.chat_completion.side_effect = error
        else:
            gateway.chat_completion.return_value = response
        gateway_cls.return_value = gateway
        yield gateway


@contextmanager
def _override_sync_db(session: Session) -> Iterator[None]:
    """Point the sync ``get_db`` (send-path template + lore lookups) at the test DB.

    The blocking-send prompt assembly runs synchronous template/lore lookups off
    the event loop; without this override they would resolve the production
    ``get_db``. The usage is read-only, so it never blocks the async writer.
    """

    def _get_db_override() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_db] = _get_db_override
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_db, None)


async def _add_message(
    session: AsyncSession, chat_id: str, role: MessageRole, content: str, **kwargs: Any
) -> Message:
    """Persist a message on the shared async session and return it (id populated)."""
    message = Message(chat_id=chat_id, role=role, content=content, **kwargs)
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


@pytest.mark.asyncio
async def test_get_messages_empty(
    async_db_session: AsyncSession, async_sample_character: Any, async_sample_model: Any
) -> None:
    """Test getting messages for a new chat with pagination wrapper"""
    chat = Chat(
        character_id=async_sample_character.id,
        model_id=async_sample_model.id,
        title="Chat",
    )
    async_db_session.add(chat)
    await async_db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/chats/{chat.id}/messages")
        assert response.status_code == 200
        data = response.json()
        # Verify pagination wrapper structure
        assert "items" in data
        assert "meta" in data
        assert data["items"] == []
        assert data["meta"]["limit"] == 10  # shared DEFAULT_PAGE_SIZE (BE-M3)
        assert data["meta"]["has_more"] is False
        assert data["meta"]["cursor"] is None  # No cursor when there are no messages


# ---------------------------------------------------------------------------
# POST "" — blocking send
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_message_blocking_returns_200_and_persists(
    async_db_session: AsyncSession, db_session: Session, async_test_chat_id: str
) -> None:
    """Blocking send returns the assistant MessageResponse and persists both turns."""
    chat_id = async_test_chat_id
    completion = CompletionResponse(
        content="Hello! How can I help you?", finish_reason="stop", usage=TokenUsage()
    )

    with _override_sync_db(db_session), _mock_provider_gateway(response=completion):
        async with _asgi_client() as client:
            response = await client.post(
                f"/api/chats/{chat_id}/messages", json={"content": "Hello"}
            )

    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "assistant"
    assert data["content"] == "Hello! How can I help you?"
    assert data["chat_id"] == chat_id
    assert data["id"]
    assert data["created_at"]

    # Both the user turn and the assistant reply are persisted, in order.
    rows = list(
        (
            await async_db_session.execute(
                select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at)
            )
        )
        .scalars()
        .all()
    )
    assert [m.role for m in rows] == [MessageRole.USER, MessageRole.ASSISTANT]
    assert rows[0].content == "Hello"
    assert rows[1].content == "Hello! How can I help you?"


@pytest.mark.asyncio
async def test_send_message_blocking_missing_content_returns_422(
    async_db_session: AsyncSession, async_test_chat_id: str
) -> None:
    """A non-regenerate send with no body is rejected before any provider call."""
    async with _asgi_client() as client:
        response = await client.post(f"/api/chats/{async_test_chat_id}/messages")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_send_message_blocking_provider_error_returns_502(
    async_db_session: AsyncSession, db_session: Session, async_test_chat_id: str
) -> None:
    """A provider fault on a blocking send maps to 502 and persists no assistant reply."""
    chat_id = async_test_chat_id

    with (
        _override_sync_db(db_session),
        _mock_provider_gateway(error=RuntimeError("upstream boom")),
    ):
        async with _asgi_client() as client:
            response = await client.post(
                f"/api/chats/{chat_id}/messages", json={"content": "Hello"}
            )

    assert response.status_code == 502
    assert response.json()["detail"] == "Error communicating with AI provider."

    # The user turn was committed before the failed completion; no blank assistant turn.
    rows = list(
        (
            await async_db_session.execute(
                select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at)
            )
        )
        .scalars()
        .all()
    )
    assert [m.role for m in rows] == [MessageRole.USER]


# ---------------------------------------------------------------------------
# POST /suggestions and POST /title
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_suggest_next_turn_returns_suggestions(
    async_db_session: AsyncSession, async_test_chat_id: str
) -> None:
    """Reply suggestions come back as a list of strings (task-model JSON array)."""
    completion = CompletionResponse(
        content='["Fight back.", "Flee.", "Negotiate."]',
        finish_reason="stop",
        usage=TokenUsage(),
    )

    with _mock_provider_gateway(response=completion):
        async with _asgi_client() as client:
            response = await client.post(
                f"/api/chats/{async_test_chat_id}/messages/suggestions",
                json={"mode": "reply", "count": 3},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["suggestions"] == ["Fight back.", "Flee.", "Negotiate."]


@pytest.mark.asyncio
async def test_generate_chat_title_returns_and_persists(
    async_db_session: AsyncSession, async_test_chat_id: str
) -> None:
    """Title generation returns the cleaned title and persists it on the chat."""
    chat_id = async_test_chat_id
    await _add_message(async_db_session, chat_id, MessageRole.USER, "Where are we headed?")
    await _add_message(async_db_session, chat_id, MessageRole.ASSISTANT, "To the frozen north.")

    completion = CompletionResponse(
        content="Journey To The North", finish_reason="stop", usage=TokenUsage()
    )

    with _mock_provider_gateway(response=completion):
        async with _asgi_client() as client:
            response = await client.post(f"/api/chats/{chat_id}/messages/title")

    assert response.status_code == 200
    assert response.json() == {"title": "Journey To The North"}

    refreshed = await async_db_session.get(Chat, chat_id)
    assert refreshed is not None
    await async_db_session.refresh(refreshed)
    assert refreshed.title == "Journey To The North"


# ---------------------------------------------------------------------------
# PUT /{message_id} — edit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_edit_message_returns_200_and_updates(
    async_db_session: AsyncSession, async_test_chat_id: str
) -> None:
    """Editing a message returns the updated content with a recomputed token count."""
    chat_id = async_test_chat_id
    message = await _add_message(async_db_session, chat_id, MessageRole.USER, "Original text")

    async with _asgi_client() as client:
        response = await client.put(
            f"/api/chats/{chat_id}/messages/{message.id}",
            json={"content": "Edited text"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == message.id
    assert data["content"] == "Edited text"
    assert data["token_count"] is not None and data["token_count"] > 0

    await async_db_session.refresh(message)
    assert message.content == "Edited text"


@pytest.mark.asyncio
async def test_edit_message_not_found_returns_404(
    async_db_session: AsyncSession, async_test_chat_id: str
) -> None:
    """Editing a message that does not exist in the chat is a 404."""
    async with _asgi_client() as client:
        response = await client.put(
            f"/api/chats/{async_test_chat_id}/messages/nonexistent_id",
            json={"content": "New content"},
        )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /{message_id}/alternatives — list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_alternatives_returns_200(
    async_db_session: AsyncSession, async_test_chat_id: str
) -> None:
    """Alternatives for a message are returned ordered by ordinal."""
    chat_id = async_test_chat_id
    message = await _add_message(
        async_db_session, chat_id, MessageRole.ASSISTANT, "current", active_index=1
    )
    async_db_session.add_all(
        [
            MessageAlternative(message_id=message.id, content="original", token_count=1, ordinal=0),
            MessageAlternative(message_id=message.id, content="current", token_count=1, ordinal=1),
        ]
    )
    await async_db_session.commit()

    async with _asgi_client() as client:
        response = await client.get(f"/api/chats/{chat_id}/messages/{message.id}/alternatives")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert [alt["content"] for alt in data] == ["original", "current"]
    assert [alt["ordinal"] for alt in data] == [0, 1]
    assert all(alt["message_id"] == message.id for alt in data)


@pytest.mark.asyncio
async def test_list_alternatives_message_not_found_returns_404(
    async_db_session: AsyncSession, async_test_chat_id: str
) -> None:
    """Listing alternatives for a missing message is a 404."""
    async with _asgi_client() as client:
        response = await client.get(
            f"/api/chats/{async_test_chat_id}/messages/nonexistent_id/alternatives"
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_alternatives_wrong_chat_returns_404(
    async_db_session: AsyncSession, async_sample_character: Any, async_sample_model: Any
) -> None:
    """A message requested under a different chat is not found (chat-scoped lookup)."""
    chat_a = Chat(character_id=async_sample_character.id, model_id=async_sample_model.id, title="A")
    chat_b = Chat(character_id=async_sample_character.id, model_id=async_sample_model.id, title="B")
    async_db_session.add_all([chat_a, chat_b])
    await async_db_session.commit()
    await async_db_session.refresh(chat_a)
    await async_db_session.refresh(chat_b)

    message = await _add_message(async_db_session, chat_a.id, MessageRole.ASSISTANT, "in chat A")

    async with _asgi_client() as client:
        response = await client.get(f"/api/chats/{chat_b.id}/messages/{message.id}/alternatives")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PUT /{message_id}/alternatives/{alternative_id}/activate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_activate_alternative_returns_200_and_switches(
    async_db_session: AsyncSession, async_test_chat_id: str
) -> None:
    """Activating an alternative switches the message's active content + index."""
    chat_id = async_test_chat_id
    message = await _add_message(
        async_db_session, chat_id, MessageRole.ASSISTANT, "current", active_index=1
    )
    alt_original = MessageAlternative(
        message_id=message.id, content="original", token_count=2, ordinal=0
    )
    alt_current = MessageAlternative(
        message_id=message.id, content="current", token_count=2, ordinal=1
    )
    async_db_session.add_all([alt_original, alt_current])
    await async_db_session.commit()
    await async_db_session.refresh(alt_original)

    async with _asgi_client() as client:
        response = await client.put(
            f"/api/chats/{chat_id}/messages/{message.id}/alternatives/{alt_original.id}/activate"
        )

    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "original"
    assert data["active_index"] == 0

    await async_db_session.refresh(message)
    assert message.content == "original"
    assert message.active_index == 0


@pytest.mark.asyncio
async def test_activate_alternative_not_found_returns_404(
    async_db_session: AsyncSession, async_test_chat_id: str
) -> None:
    """Activating an alternative that does not exist for the message is a 404."""
    chat_id = async_test_chat_id
    message = await _add_message(async_db_session, chat_id, MessageRole.ASSISTANT, "current")

    async with _asgi_client() as client:
        response = await client.put(
            f"/api/chats/{chat_id}/messages/{message.id}/alternatives/nonexistent_id/activate"
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_activate_alternative_wrong_chat_returns_404(
    async_db_session: AsyncSession, async_sample_character: Any, async_sample_model: Any
) -> None:
    """Activating an alternative via the wrong chat is a 404 (chat-scoped message lookup)."""
    chat_a = Chat(character_id=async_sample_character.id, model_id=async_sample_model.id, title="A")
    chat_b = Chat(character_id=async_sample_character.id, model_id=async_sample_model.id, title="B")
    async_db_session.add_all([chat_a, chat_b])
    await async_db_session.commit()
    await async_db_session.refresh(chat_a)
    await async_db_session.refresh(chat_b)

    message = await _add_message(async_db_session, chat_a.id, MessageRole.ASSISTANT, "in chat A")
    alt = MessageAlternative(message_id=message.id, content="alt", token_count=1, ordinal=0)
    async_db_session.add(alt)
    await async_db_session.commit()
    await async_db_session.refresh(alt)

    async with _asgi_client() as client:
        response = await client.put(
            f"/api/chats/{chat_b.id}/messages/{message.id}/alternatives/{alt.id}/activate"
        )

    assert response.status_code == 404
