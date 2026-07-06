"""Test concurrent streaming requests"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from src.main import app
from src.provider import Provider
from src.provider.adapters import StreamChunk


@pytest.mark.asyncio
async def test_concurrent_streaming(async_test_chat_id: str, test_api_key_env, async_db_session):
    """Test 10 concurrent streaming requests (should not block each other)"""

    # Mock the provider client to return streaming chunks
    async def mock_stream(api_messages):
        yield StreamChunk(content="Response")
        yield StreamChunk(content=" chunk")
        yield StreamChunk(finish_reason="stop")

    async def stream_request(client: AsyncClient, request_id: int):
        """Single streaming request"""
        response = await client.post(
            f"/api/chats/{async_test_chat_id}/messages/stream",
            json={"content": f"Request {request_id}"},
        )

        chunk_count = 0
        async for _ in response.aiter_lines():
            chunk_count += 1

        return chunk_count

    with (
        patch.object(Provider, "has_api_key", return_value=True),
        patch("src.chat_message.service.ProviderGateway") as mock_gateway_class,
    ):
        mock_client = AsyncMock()
        mock_client.chat_completion_stream = mock_stream
        mock_gateway_class.return_value = mock_client

        # Run 10 concurrent requests
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as client:
            tasks = [stream_request(client, i) for i in range(10)]
            results = await asyncio.gather(*tasks)

    # All requests should complete
    assert len(results) == 10
    assert all(count > 0 for count in results)
