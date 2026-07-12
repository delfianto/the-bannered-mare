"""Integration test for message streaming"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
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
