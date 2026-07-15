"""Tests for AsyncBaseRepository.

Mirrors ``test_base_repository.py`` for the async twin, exercising the surface
ported for parity: ``find_all_ordered`` and ``find_paginated_ordered`` (incl.
filters + the limit guard).
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from src.core.persistence import AsyncBaseRepository, BaseModel


class MockAsyncModel(BaseModel):
    """Simple model for testing the async base repository."""

    __tablename__ = "mock_async_models"
    name: Mapped[str] = mapped_column(String(50), nullable=False)


class MockAsyncRepository(AsyncBaseRepository[MockAsyncModel]):
    """Async repository over MockAsyncModel."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, MockAsyncModel)


@pytest.mark.asyncio
async def test_find_all_ordered_defaults_to_newest_first(async_db_session: AsyncSession) -> None:
    """Default ordering is ``created_at`` desc (newest-first)."""
    repo = MockAsyncRepository(async_db_session)
    base = datetime(2020, 1, 1, tzinfo=UTC)
    for i, name in enumerate(("a", "b", "c")):
        entity = MockAsyncModel(name=name)
        entity.created_at = base + timedelta(days=i)  # deterministic ordering
        _ = await repo.create(entity)
    await repo.db.commit()

    ordered = await repo.find_all_ordered()
    assert [m.name for m in ordered] == ["c", "b", "a"]


@pytest.mark.asyncio
async def test_find_all_ordered_honours_explicit_order_by(async_db_session: AsyncSession) -> None:
    """An explicit ``order_by`` overrides the default."""
    repo = MockAsyncRepository(async_db_session)
    for name in ("charlie", "alpha", "bravo"):
        _ = await repo.create(MockAsyncModel(name=name))
    await repo.db.commit()

    ordered = await repo.find_all_ordered(order_by=MockAsyncModel.name.asc())
    assert [m.name for m in ordered] == ["alpha", "bravo", "charlie"]


@pytest.mark.asyncio
async def test_find_paginated_ordered(async_db_session: AsyncSession) -> None:
    """Ordered paginated retrieval + total count."""
    repo = MockAsyncRepository(async_db_session)
    for i in range(15):
        _ = await repo.create(MockAsyncModel(name=str(i)))
    await repo.db.commit()

    page1, total = await repo.find_paginated_ordered(limit=10, offset=0)
    assert len(page1) == 10
    assert total == 15

    page2, total = await repo.find_paginated_ordered(limit=10, offset=10)
    assert len(page2) == 5
    assert total == 15


@pytest.mark.asyncio
async def test_find_paginated_ordered_applies_filters(async_db_session: AsyncSession) -> None:
    """The ``filters`` dict narrows both the page and the total count."""
    repo = MockAsyncRepository(async_db_session)
    for name in ("keep", "keep", "drop"):
        _ = await repo.create(MockAsyncModel(name=name))
    await repo.db.commit()

    items, total = await repo.find_paginated_ordered(filters={"name": "keep"})
    assert total == 2
    assert {m.name for m in items} == {"keep"}


@pytest.mark.asyncio
async def test_find_paginated_ordered_rejects_oversized_limit(
    async_db_session: AsyncSession,
) -> None:
    """Requesting more than ``MAX_LIMIT`` raises, mirroring the sync guard."""
    repo = MockAsyncRepository(async_db_session)
    with pytest.raises(ValueError):
        _ = await repo.find_paginated_ordered(limit=MockAsyncRepository.MAX_LIMIT + 1)
