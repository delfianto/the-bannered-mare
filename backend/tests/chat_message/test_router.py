"""Tests for chat message router"""

from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.chat_session.models import Chat
from src.main import app


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
        assert data["meta"]["limit"] == 20
        assert data["meta"]["has_more"] is False
        assert data["meta"]["cursor"] is None  # No cursor when there are no messages
