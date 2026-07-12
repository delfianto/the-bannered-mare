"""Tests for async message repository"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.chat_message.models import Message, MessageRole
from src.chat_message.repository_async import AsyncMessageRepository


@pytest.mark.asyncio
async def test_create_message(async_db_session: AsyncSession, async_test_chat_id: str):
    """Test creating a message"""
    repo = AsyncMessageRepository(async_db_session)

    message = Message(
        chat_id=async_test_chat_id,
        role=MessageRole.USER,
        content="Hello world",
        token_count=2,
    )

    created = await repo.create(message)
    await repo.commit()

    assert created.id is not None
    assert created.content == "Hello world"


@pytest.mark.asyncio
async def test_find_by_chat_id(async_db_session: AsyncSession, async_test_chat_id: str):
    """Test finding messages by chat ID"""
    repo = AsyncMessageRepository(async_db_session)

    # Create test messages
    for i in range(3):
        msg = Message(
            chat_id=async_test_chat_id,
            role=MessageRole.USER,
            content=f"Message {i}",
            token_count=2,
        )
        await repo.create(msg)

    await repo.commit()

    # Find messages
    messages = await repo.find_by_chat_id(async_test_chat_id)

    assert len(messages) == 3
    assert messages[0].content == "Message 0"  # Ordered by created_at


@pytest.mark.asyncio
async def test_find_by_chat_id_caps_to_newest_ascending(
    async_db_session: AsyncSession, async_test_chat_id: str
):
    """With a limit, the newest N messages are returned in chronological order."""
    repo = AsyncMessageRepository(async_db_session)
    for i in range(5):
        await repo.create(
            Message(
                chat_id=async_test_chat_id,
                role=MessageRole.USER,
                content=f"Message {i}",
                token_count=2,
            )
        )
    await repo.commit()

    messages = await repo.find_by_chat_id(async_test_chat_id, limit=2)

    # Newest two, oldest-first: Message 3 then Message 4.
    assert [m.content for m in messages] == ["Message 3", "Message 4"]
