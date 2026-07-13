"""Tests for BaseRepository"""

import pytest
from sqlalchemy import String
from sqlalchemy.orm import Mapped, Session, mapped_column
from src.core.persistence import BaseModel, BaseRepository


class MockModel(BaseModel):
    """Simple model for testing BaseRepository"""

    __tablename__ = "mock_models"
    name: Mapped[str] = mapped_column(String(50), nullable=False)


class MockRepository(BaseRepository[MockModel]):
    """Repository for MockModel"""

    def __init__(self, db: Session) -> None:
        super().__init__(db, MockModel)


@pytest.fixture(scope="function")
def repo(db: Session) -> MockRepository:
    """Fixture for MockRepository"""
    # Register MockModel with metadata for this test session
    # Use metadata.create_all to be safer with types
    MockModel.metadata.create_all(db.get_bind())
    return MockRepository(db)


def test_create_and_find_by_id(repo: MockRepository) -> None:
    """Test creating and finding an entity (manual commit)"""
    obj = MockModel(name="Test")
    created = repo.create(obj)
    _ = repo.commit()

    found = repo.find_by_id(created.id)
    assert found is not None
    assert found.name == "Test"
    assert found.id == created.id


def test_find_all(repo: MockRepository) -> None:
    """Test finding all entities"""
    _ = repo.create(MockModel(name="1"))
    _ = repo.create(MockModel(name="2"))
    repo.commit()

    all_objs = repo.find_all()
    assert len(all_objs) == 2


def test_find_paginated_ordered(repo: MockRepository) -> None:
    """Test ordered paginated retrieval + total count"""
    for i in range(15):
        _ = repo.create(MockModel(name=str(i)))
    repo.commit()

    page1, total = repo.find_paginated_ordered(limit=10, offset=0)
    assert len(page1) == 10
    assert total == 15

    page2, total = repo.find_paginated_ordered(limit=10, offset=10)
    assert len(page2) == 5
    assert total == 15


def test_update_pattern(repo: MockRepository) -> None:
    """Test updating an entity using update + commit"""
    obj = MockModel(name="Old")
    _ = repo.create(obj)
    repo.commit()

    obj.name = "New"
    _ = repo.update(obj)
    repo.commit()

    assert obj.name == "New"
    result = repo.find_by_id(obj.id)
    assert result is not None
    assert result.name == "New"


def test_update_rollback(repo: MockRepository) -> None:
    """Test updating an entity without committing (manual rollback)"""
    obj = MockModel(name="Old")
    _ = repo.create(obj)
    repo.commit()

    obj.name = "Flushed"
    _ = repo.update(obj)

    # We rollback to check it wasn't committed
    _ = repo.rollback()

    # It should still be "Old" in DB because flush was rolled back
    result = repo.find_by_id(obj.id)
    assert result is not None
    assert result.name == "Old"


def test_delete_pattern(repo: MockRepository) -> None:
    """Test deleting an entity using delete + commit"""
    obj = MockModel(name="DeleteMe")
    _ = repo.create(obj)
    repo.commit()
    obj_id = obj.id

    _ = repo.delete(obj)
    repo.commit()

    assert repo.find_by_id(obj_id) is None


def test_count_and_exists(repo: MockRepository) -> None:
    """Test count and exists methods"""
    obj = MockModel(name="CountMe")
    _ = repo.create(obj)
    repo.commit()

    assert repo.count() == 1
    assert repo.exists(obj.id) is True
    assert repo.exists("nonexistent") is False
