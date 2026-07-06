"""Integration test for message regeneration streaming"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from src.chat_message.models import Message, MessageRole
from src.chat_session.models import Chat
from src.core.persistence import get_db
from src.main import app
from src.provider import Provider
from src.provider.adapters import StreamChunk


@pytest.mark.asyncio
async def test_regenerate_message_stream(
    async_db_session, db_session, async_sample_character, async_sample_model, test_api_key_env
):
    """Test regenerating message via streaming endpoint returns structured events"""
    chat = Chat(
        character_id=async_sample_character.id,
        model_id=async_sample_model.id,
        title="Regen Chat",
    )
    async_db_session.add(chat)
    await async_db_session.commit()
    await async_db_session.refresh(chat)

    msg1 = Message(chat_id=chat.id, role=MessageRole.USER, content="Hello")
    msg2 = Message(chat_id=chat.id, role=MessageRole.ASSISTANT, content="Bad response")
    async_db_session.add_all([msg1, msg2])
    await async_db_session.commit()

    async def mock_stream(api_messages):
        yield StreamChunk(content="Better ")
        yield StreamChunk(content="response")
        yield StreamChunk(finish_reason="stop")

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with (
            patch.object(Provider, "has_api_key", return_value=True),
            patch("src.chat_message.service.ProviderGateway") as mock_gateway_class,
        ):
            mock_client = AsyncMock()
            mock_client.chat_completion_stream = mock_stream
            mock_gateway_class.return_value = mock_client

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/chats/{chat.id}/messages?stream=true&regenerate=true",
                )

                assert response.status_code == 200
                assert "text/event-stream" in response.headers["content-type"]

                events = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        events.append(json.loads(line[6:]))

                assert events[0]["type"] == "start"

                text_events = [e for e in events if e["type"] == "text"]
                full_text = "".join(e["content"] for e in text_events)
                assert "Better" in full_text

                assert events[-1]["type"] == "done"

    finally:
        app.dependency_overrides.pop(get_db, None)
