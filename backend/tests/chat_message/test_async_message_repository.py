"""Tests for async message repository"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.chat_message.models import Message, MessageRole
from src.chat_message.repository_async import AsyncMessageRepository

# Fixed base timestamp so cursor-pagination boundaries are deterministic instead
# of depending on the sub-millisecond spacing of ``created_at``'s insert default.
_BASE_TIME = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)


def _msg(chat_id: str, index: int, created_at: datetime) -> Message:
    return Message(
        chat_id=chat_id,
        role=MessageRole.USER,
        content=f"Message {index}",
        token_count=2,
        created_at=created_at,
    )


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


@pytest.mark.asyncio
async def test_find_by_chat_id_empty_chat_returns_empty(
    async_db_session: AsyncSession, async_test_chat_id: str
):
    """A chat with no messages returns an empty list, not an error."""
    repo = AsyncMessageRepository(async_db_session)
    assert await repo.find_by_chat_id(async_test_chat_id) == []


# ---------------------------------------------------------------------------
# find_latest_by_chat_id — the reverse-chronological cursor used for pagination
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_latest_orders_newest_first_and_caps_to_limit(
    async_db_session: AsyncSession, async_test_chat_id: str
):
    """No cursor: returns the newest ``limit`` messages, newest-first."""
    repo = AsyncMessageRepository(async_db_session)
    for i in range(5):
        await repo.create(_msg(async_test_chat_id, i, _BASE_TIME + timedelta(minutes=i)))
    await repo.commit()

    page = await repo.find_latest_by_chat_id(async_test_chat_id, limit=3)

    assert [m.content for m in page] == ["Message 4", "Message 3", "Message 2"]


@pytest.mark.asyncio
async def test_find_latest_before_cursor_is_exclusive(
    async_db_session: AsyncSession, async_test_chat_id: str
):
    """The ``before`` cursor is strict: the row AT the cursor time is excluded."""
    repo = AsyncMessageRepository(async_db_session)
    for i in range(5):
        await repo.create(_msg(async_test_chat_id, i, _BASE_TIME + timedelta(minutes=i)))
    await repo.commit()

    cursor = _BASE_TIME + timedelta(minutes=3)  # Message 3's timestamp
    page = await repo.find_latest_by_chat_id(async_test_chat_id, limit=10, before=cursor)

    # Message 3 (== cursor) and Message 4 (> cursor) are both excluded.
    assert [m.content for m in page] == ["Message 2", "Message 1", "Message 0"]


@pytest.mark.asyncio
async def test_find_latest_walks_full_history_page_by_page(
    async_db_session: AsyncSession, async_test_chat_id: str
):
    """Feeding each page's oldest ``created_at`` back as the cursor walks the whole
    history exactly once, and past the oldest message yields nothing."""
    repo = AsyncMessageRepository(async_db_session)
    for i in range(5):
        await repo.create(_msg(async_test_chat_id, i, _BASE_TIME + timedelta(minutes=i)))
    await repo.commit()

    first = await repo.find_latest_by_chat_id(async_test_chat_id, limit=2)
    assert [m.content for m in first] == ["Message 4", "Message 3"]

    second = await repo.find_latest_by_chat_id(
        async_test_chat_id, limit=2, before=first[-1].created_at
    )
    assert [m.content for m in second] == ["Message 2", "Message 1"]

    third = await repo.find_latest_by_chat_id(
        async_test_chat_id, limit=2, before=second[-1].created_at
    )
    assert [m.content for m in third] == ["Message 0"]

    beyond = await repo.find_latest_by_chat_id(
        async_test_chat_id, limit=2, before=third[-1].created_at
    )
    assert beyond == []


@pytest.mark.asyncio
async def test_find_latest_same_created_at_current_behavior(
    async_db_session: AsyncSession, async_test_chat_id: str
):
    """Pin today's behavior when several messages share one ``created_at``.

    The ORDER BY is ``created_at`` desc only — there is no secondary ``id``
    tie-breaker — so the relative order *among* same-instant rows is unspecified
    (asserted as a set). And because the cursor filter is strict ``< before``, a
    cursor AT the tied instant skips *every* row at that instant. This documents
    the current contract; adding the id tie-breaker is tracked separately (BE-M2).
    Production code is intentionally left unchanged here.
    """
    repo = AsyncMessageRepository(async_db_session)
    tie = _BASE_TIME + timedelta(minutes=5)
    await repo.create(_msg(async_test_chat_id, 0, _BASE_TIME + timedelta(minutes=4)))
    for i in (1, 2, 3):
        await repo.create(_msg(async_test_chat_id, i, tie))  # three rows share `tie`
    await repo.create(_msg(async_test_chat_id, 4, _BASE_TIME + timedelta(minutes=6)))
    await repo.commit()

    page = await repo.find_latest_by_chat_id(async_test_chat_id, limit=10)

    # The strictly newer/older rows bracket the page deterministically ...
    assert page[0].content == "Message 4"
    assert page[-1].content == "Message 0"
    # ... with the three tied rows between them, order among them unspecified.
    assert {m.content for m in page[1:4]} == {"Message 1", "Message 2", "Message 3"}

    # A cursor AT the tied instant drops ALL three tied rows (strict ``<``),
    # leaving only the strictly-older row — the known cursor gap when ties exist.
    older = await repo.find_latest_by_chat_id(async_test_chat_id, limit=10, before=tie)
    assert [m.content for m in older] == ["Message 0"]
