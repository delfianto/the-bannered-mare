"""Tests for ModelFamilyService"""

from typing import Any

import pytest
from sqlalchemy.orm import Session
from src.core.exceptions import BanneredMareException, NotFoundError
from src.model_family import (
    ModelFamily,
    ModelFamilyCreate,
    ModelFamilyRepository,
    ModelFamilyService,
    ModelFamilyUpdate,
)


class TestModelFamilyService:
    """Test suite for ModelFamilyService"""

    def test_list_all(self, db: Session, sample_family: Any) -> None:
        """Test listing all model families"""
        family2 = ModelFamily(
            name="Claude",
            family_identifier="test.claude",
            description="Claude family",
            provider_types=["anthropic"],
        )
        db.add(family2)
        db.commit()

        repo = ModelFamilyRepository(db)
        service = ModelFamilyService(repo)
        families = service.list_all()

        assert len(families) >= 2
        assert any(f.name == "GPT" for f in families)
        assert any(f.name == "Claude" for f in families)

    def test_list_paginated(self, db: Session, sample_family: Any) -> None:
        """Test listing model families with pagination"""
        family2 = ModelFamily(
            name="Claude",
            family_identifier="test.claude",
            description="Claude family",
            provider_types=["anthropic"],
        )
        db.add(family2)
        db.commit()

        repo = ModelFamilyRepository(db)
        service = ModelFamilyService(repo)

        # Test limit
        items, total = service.list_paginated(limit=1, offset=0)
        assert len(items) == 1
        assert total >= 2

        # Test offset
        items, total = service.list_paginated(limit=1, offset=1)
        assert len(items) == 1
        assert total >= 2

    def test_list_paginated_orders_by_name_case_insensitive(self, db: Session) -> None:
        """list_paginated returns families alphabetically by name, ignoring case."""
        # ci order ("apex, banana, Mango, Zeta") differs from raw ASCII order.
        for i, name in enumerate(["Zeta", "apex", "Mango", "banana"]):
            db.add(
                ModelFamily(
                    name=name,
                    family_identifier=f"test.fam-{i}",
                    provider_types=["openai"],
                )
            )
        db.commit()

        repo = ModelFamilyRepository(db)
        service = ModelFamilyService(repo)

        families, total = service.list_paginated(limit=10, offset=0)

        assert total == 4
        assert [f.name for f in families] == ["apex", "banana", "Mango", "Zeta"]

    def test_list_paginated_filters_by_name(self, db: Session) -> None:
        """The name__ilike filter matches case-insensitively on the family name."""
        for name, ident in [
            ("Claude Sonnet", "test.claude-sonnet"),
            ("GPT-4o", "test.gpt-4o"),
            ("Claude Opus", "test.claude-opus"),
        ]:
            db.add(ModelFamily(name=name, family_identifier=ident, provider_types=["openai"]))
        db.commit()

        repo = ModelFamilyRepository(db)
        service = ModelFamilyService(repo)

        families, total = service.list_paginated(filters={"name__ilike": "claude"})

        assert total == 2
        assert all("claude" in f.name.lower() for f in families)

    def test_get_by_id_success(self, db: Session, sample_family: Any) -> None:
        """Test getting a model family by ID successfully"""
        repo = ModelFamilyRepository(db)
        service = ModelFamilyService(repo)
        result = service.get_by_id(sample_family.id)

        assert result.id == sample_family.id
        assert result.name == "GPT"

    def test_get_by_id_not_found(self, db: Session) -> None:
        """Test getting a family that doesn't exist raises 404"""
        repo = ModelFamilyRepository(db)
        service = ModelFamilyService(repo)

        with pytest.raises(NotFoundError) as exc_info:
            _ = service.get_by_id("nonexistent-id")

        assert exc_info.value.status_code == 404

    def test_get_first_returns_a_family(self, db: Session, sample_family: Any) -> None:
        """get_first returns a configured family (the model-discovery fallback)."""
        service = ModelFamilyService(ModelFamilyRepository(db))

        result = service.get_first()

        assert result is not None
        assert result.id == sample_family.id

    def test_get_first_returns_none_when_empty(self, db: Session) -> None:
        """get_first returns None when no families are configured."""
        service = ModelFamilyService(ModelFamilyRepository(db))

        assert service.get_first() is None

    def test_create_family_success(self, db: Session) -> None:
        """Test creating a model family successfully"""
        repo = ModelFamilyRepository(db)
        service = ModelFamilyService(repo)

        family_data = ModelFamilyCreate(
            name="GPT-New",
            family_identifier="test.gpt-new",
            description="GPT model family",
            provider_types=["openai"],
            parameters={
                "temperature": {"type": "float", "default": 0.7, "min_value": 0, "max_value": 2},
                "max_tokens": {"type": "int", "default": 2048, "min_value": 1},
            },
            unsupported_parameters=[],
            extra_metadata={"version": "1.0"},
        )
        family = service.create(family_data)

        assert family.name == "GPT-New"
        assert family.description == "GPT model family"
        assert "openai" in family.provider_types
        assert family.parameters["temperature"]["default"] == 0.7
        assert family.extra_metadata == {"version": "1.0"}

    def test_create_family_minimal(self, db: Session) -> None:
        """Test creating a family with minimal fields"""
        repo = ModelFamilyRepository(db)
        service = ModelFamilyService(repo)

        family_data = ModelFamilyCreate(
            name="GPT-Min",
            family_identifier="test.gpt-min",
            description=None,
            provider_types=[],
            parameters={},
            unsupported_parameters=[],
            extra_metadata=None,
        )
        family = service.create(family_data)

        assert family.name == "GPT-Min"
        assert family.description is None
        assert family.provider_types == []
        assert family.parameters == {}
        assert family.extra_metadata is None

    def test_create_family_duplicate_name(self, db: Session, sample_family: Any) -> None:
        """Test creating a family with duplicate name raises error"""
        # Try to create duplicate
        repo = ModelFamilyRepository(db)
        service = ModelFamilyService(repo)
        family_data = ModelFamilyCreate(
            name="GPT", family_identifier="test.gpt-dup", description=None, extra_metadata=None
        )
        with pytest.raises(BanneredMareException) as exc_info:
            _ = service.create(family_data)

        assert exc_info.value.status_code == 409
        assert "already exists" in exc_info.value.message.lower()

    def test_update_family_all_fields(self, db: Session, sample_family: Any) -> None:
        """Test updating all family fields"""
        repo = ModelFamilyRepository(db)
        service = ModelFamilyService(repo)
        family_data = ModelFamilyUpdate(
            name="GPT Updated",
            family_identifier="test.gpt-updated",
            description="New description",
            provider_types=["custom"],
            parameters={
                "temperature": {"type": "float", "default": 0.8, "min_value": 0, "max_value": 1}
            },
            extra_metadata={"updated": True},
        )
        updated = service.update(sample_family.id, family_data)

        assert updated.name == "GPT Updated"
        assert updated.description == "New description"
        assert "custom" in updated.provider_types
        assert updated.parameters["temperature"]["default"] == 0.8
        assert updated.extra_metadata == {"updated": True}

    def test_update_family_partial(self, db: Session, sample_family: Any) -> None:
        """Test updating only some fields"""
        repo = ModelFamilyRepository(db)
        service = ModelFamilyService(repo)
        family_data = ModelFamilyUpdate.model_construct(description="Updated description")
        updated = service.update(sample_family.id, family_data)

        assert updated.name == "GPT"  # Unchanged
        assert updated.description == "Updated description"  # Changed

    def test_update_family_not_found(self, db: Session) -> None:
        """Test updating non-existent family raises 404"""
        repo = ModelFamilyRepository(db)
        service = ModelFamilyService(repo)

        family_data = ModelFamilyUpdate.model_construct(name="New Name")
        with pytest.raises(NotFoundError) as exc_info:
            _ = service.update("nonexistent-id", family_data)

        assert exc_info.value.status_code == 404

    def test_delete_family_success(self, db: Session, sample_family: Any) -> None:
        """Test deleting a family successfully"""
        family_id = sample_family.id

        repo = ModelFamilyRepository(db)
        service = ModelFamilyService(repo)
        service.delete(family_id)

        # Verify family is deleted
        deleted = db.query(ModelFamily).filter(ModelFamily.id == family_id).first()
        assert deleted is None

    def test_delete_family_in_use(self, db: Session, sample_model: Any) -> None:
        """Test deleting a family that is in use raises error"""
        family_id = sample_model.model_family_id

        # Try to delete family
        repo = ModelFamilyRepository(db)
        service = ModelFamilyService(repo)
        with pytest.raises(BanneredMareException) as exc_info:
            service.delete(family_id)

        assert exc_info.value.status_code == 409
        assert "being used" in exc_info.value.message.lower()

    def test_delete_family_not_found(self, db: Session) -> None:
        """Test deleting non-existent family raises 404"""
        repo = ModelFamilyRepository(db)
        service = ModelFamilyService(repo)

        with pytest.raises(NotFoundError) as exc_info:
            service.delete("nonexistent-id")

        assert exc_info.value.status_code == 404
