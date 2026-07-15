"""Tests for AsyncBaseRepository and its async mixins.

Mirrors ``test_base_repository.py`` for the async twin, exercising the surface
ported for parity: ``find_all_ordered``, ``find_paginated_ordered`` (incl.
filters + the limit guard) and the ``AsyncNamedRepository`` /
``AsyncDefaultableRepository`` mixins.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Boolean, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from src.core.persistence import (
    AsyncDefaultableRepository,
    AsyncNamedRepository,
    BaseModel,
)


class MockAsyncModel(BaseModel):
    """Simple model for testing the async base repository + mixins."""

    __tablename__ = "mock_async_models"
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class MockAsyncRepository(
    AsyncNamedRepository[MockAsyncModel], AsyncDefaultableRepository[MockAsyncModel]
):
    """Repository combining both async mixins over MockAsyncModel."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, MockAsyncModel)


async def _default_ids(session: AsyncSession) -> list[str]:
    """IDs of rows currently flagged ``is_default``, read straight from the DB.

    Reads scalar column values (not entities) so identity-map state can't mask a
    stale flag after a bulk UPDATE.
    """
    result = await session.execute(select(MockAsyncModel.id).where(MockAsyncModel.is_default))
    return [row[0] for row in result.all()]


@pytest.mark.asyncio
async def test_find_all_ordered_defaults_to_newest_first(async_db_session: AsyncSession) -> None:
    """Default ordering is ``created_at`` desc (newest-first)."""
    repo = MockAsyncRepository(async_db_session)
    base = datetime(2020, 1, 1, tzinfo=UTC)
    for i, name in enumerate(("a", "b", "c")):
        entity = MockAsyncModel(name=name)
        entity.created_at = base + timedelta(days=i)  # deterministic ordering
        _ = await repo.create(entity)
    await repo.commit()

    ordered = await repo.find_all_ordered()
    assert [m.name for m in ordered] == ["c", "b", "a"]


@pytest.mark.asyncio
async def test_find_all_ordered_honours_explicit_order_by(async_db_session: AsyncSession) -> None:
    """An explicit ``order_by`` overrides the default."""
    repo = MockAsyncRepository(async_db_session)
    for name in ("charlie", "alpha", "bravo"):
        _ = await repo.create(MockAsyncModel(name=name))
    await repo.commit()

    ordered = await repo.find_all_ordered(order_by=MockAsyncModel.name.asc())
    assert [m.name for m in ordered] == ["alpha", "bravo", "charlie"]


@pytest.mark.asyncio
async def test_find_paginated_ordered(async_db_session: AsyncSession) -> None:
    """Ordered paginated retrieval + total count."""
    repo = MockAsyncRepository(async_db_session)
    for i in range(15):
        _ = await repo.create(MockAsyncModel(name=str(i)))
    await repo.commit()

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
    await repo.commit()

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


@pytest.mark.asyncio
async def test_find_by_name(async_db_session: AsyncSession) -> None:
    """AsyncNamedRepository.find_by_name resolves the unique ``name`` column."""
    repo = MockAsyncRepository(async_db_session)
    _ = await repo.create(MockAsyncModel(name="Unique"))
    await repo.commit()

    found = await repo.find_by_name("Unique")
    assert found is not None
    assert found.name == "Unique"
    assert await repo.find_by_name("missing") is None


@pytest.mark.asyncio
async def test_set_default_keeps_a_single_default(async_db_session: AsyncSession) -> None:
    """AsyncDefaultableRepository.set_default flips exactly one row default at a time."""
    repo = MockAsyncRepository(async_db_session)
    a, b, c = (MockAsyncModel(name=n) for n in ("a", "b", "c"))
    for entity in (a, b, c):
        _ = await repo.create(entity)
    await repo.commit()

    await repo.set_default(b.id)
    await repo.commit()
    assert await _default_ids(async_db_session) == [b.id]

    # Switching the default clears the previously-set one.
    await repo.set_default(c.id)
    await repo.commit()
    assert await _default_ids(async_db_session) == [c.id]

    await repo.unset_all_defaults()
    await repo.commit()
    assert await _default_ids(async_db_session) == []
