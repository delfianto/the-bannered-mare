"""Regression test for the unified two-DB test harness (tracker BE-H8).

The sync (`sqlite` / sqlite3) and async (`sqlite+aiosqlite`) sessions used to bind to
two SEPARATE in-memory SQLite databases with no shared storage. A row committed
through the sync path was therefore invisible to the async path — a phantom
"not found" that cannot happen against the single production Postgres, but that
silently defeated any cross-path integration test.

Both sessions now bind to one shared on-disk SQLite database. This test writes a row
through the SYNC repository and reads it back through the ASYNC session, proving the
two fixtures serve one coherent database and the phantom-not-found trap is gone.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from src.character import Character, CharacterRepository


@pytest.mark.asyncio
async def test_sync_write_is_visible_to_async_read(
    db: Session, async_db_session: AsyncSession
) -> None:
    """A row committed via the sync repository is found via the async session."""
    repo = CharacterRepository(db)
    created = repo.create(Character(name="Cross Session", description="written via sync path"))
    db.commit()

    found = (
        await async_db_session.execute(
            select(Character).where(Character.id == created.id)
        )
    ).scalar_one_or_none()

    assert found is not None, (
        "async session could not read a row committed by the sync session — "
        "the two test engines are not bound to the same database"
    )
    assert found.name == "Cross Session"
