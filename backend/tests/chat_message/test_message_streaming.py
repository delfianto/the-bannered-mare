"""Integration test for message streaming"""

import json
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from src.chat_message.schemas import StreamEvent
from src.chat_message.service import ChatMessageService
from src.core.exceptions import ProviderRateLimitError
from src.core.persistence import get_db
from src.main import app
from src.provider import Provider
from src.provider.adapters import StreamChunk


@pytest.mark.asyncio
async def test_send_message_stream(
    async_test_chat_id: str, test_api_key_env, async_db_session, db_session
):
    """Test streaming message endpoint returns structured events"""

    async def mock_stream(api_messages):
        yield StreamChunk(content="Hello")
        yield StreamChunk(content=" from")
        yield StreamChunk(content=" AI")
        yield StreamChunk(finish_reason="stop")

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with (
            patch.object(Provider, "has_api_key", return_value=True),
            patch("src.chat_message.gateway_factory.ProviderGateway") as mock_gateway_class,
        ):
            mock_client = AsyncMock()
            mock_client.chat_completion_stream = mock_stream
            mock_gateway_class.return_value = mock_client

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/chats/{async_test_chat_id}/messages?stream=true",
                    json={"content": "Hello AI"},
                )

                assert response.status_code == 200
                assert "text/event-stream" in response.headers["content-type"]

                events = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        events.append(json.loads(line[6:]))

                assert len(events) > 0
                assert events[0]["type"] == "start"
                assert "message_id" in events[0]

                text_events = [e for e in events if e["type"] == "text"]
                assert len(text_events) == 3

                assert events[-1]["type"] == "done"
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_stream_setup_error_is_classified(
    async_test_chat_id: str, test_api_key_env, async_db_session, db_session
):
    """An error escaping the stream *setup* (before _stream_completion yields) is
    surfaced with a classified code, not a flat 'internal_error'."""

    async def boom_stream(self, chat_id: str, content: str) -> AsyncIterator[StreamEvent]:
        raise ProviderRateLimitError("slow down")
        yield StreamEvent(type="done")  # pragma: no cover — marks this an async generator

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with patch.object(ChatMessageService, "send_message_stream", boom_stream):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/chats/{async_test_chat_id}/messages?stream=true",
                    json={"content": "Hello AI"},
                )

                assert response.status_code == 200
                events = [
                    json.loads(line[6:])
                    async for line in response.aiter_lines()
                    if line.startswith("data: ")
                ]

        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) == 1
        # Classified from ProviderRateLimitError — not the old hardcoded fallback.
        assert error_events[0]["code"] == "rate_limit"
        assert error_events[0]["code"] != "internal_error"
    finally:
        app.dependency_overrides.pop(get_db, None)
