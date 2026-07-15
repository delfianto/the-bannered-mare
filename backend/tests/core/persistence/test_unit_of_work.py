"""BE-H1 acceptance: the UnitOfWork commits/rolls back the whole unit atomically.

Two repositories share one ``UnitOfWork``'s session; a mid-operation failure
(before ``commit``) must discard EVERY repo's flushed write, not just the last
one — the guarantee the old per-repo ``repo.commit()`` obscured (any repo could
commit the whole shared session). In production ``get_db`` rolls the session back
on an unhandled exception; here we drive ``uow.rollback()`` to assert the same.
"""

import pytest
from sqlalchemy import String
from sqlalchemy.orm import Mapped, Session, mapped_column
from src.core.persistence import BaseModel, BaseRepository, UnitOfWork


class _UowModelA(BaseModel):
    __tablename__ = "uow_model_a"
    name: Mapped[str] = mapped_column(String(50), nullable=False)


class _UowModelB(BaseModel):
    __tablename__ = "uow_model_b"
    name: Mapped[str] = mapped_column(String(50), nullable=False)


@pytest.fixture(scope="function")
def uow_tables(db: Session) -> None:
    """Create the throwaway tables (shared Base metadata) for this test session."""
    _UowModelA.metadata.create_all(db.get_bind())


def test_rollback_discards_all_writes_in_the_unit(db: Session, uow_tables: None) -> None:
    uow = UnitOfWork(db)
    repo_a = BaseRepository(db, _UowModelA)
    repo_b = BaseRepository(db, _UowModelB)

    # Two writes through DIFFERENT repos sharing the unit's session, both flushed
    # (visible in-session) but not committed.
    a = repo_a.create(_UowModelA(name="a"))
    b = repo_b.create(_UowModelB(name="b"))
    a_id, b_id = a.id, b.id

    # A failure before uow.commit() → the whole unit is rolled back.
    uow.rollback()

    assert repo_a.find_by_id(a_id) is None
    assert repo_b.find_by_id(b_id) is None


def test_commit_persists_all_writes_in_the_unit(db: Session, uow_tables: None) -> None:
    uow = UnitOfWork(db)
    repo_a = BaseRepository(db, _UowModelA)
    repo_b = BaseRepository(db, _UowModelB)

    a_id = repo_a.create(_UowModelA(name="a")).id
    b_id = repo_b.create(_UowModelB(name="b")).id
    uow.commit()

    assert repo_a.find_by_id(a_id) is not None
    assert repo_b.find_by_id(b_id) is not None
