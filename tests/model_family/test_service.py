"""Tests for ModelFamilyService"""

from typing import Any

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session
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

        with pytest.raises(HTTPException) as exc_info:
            _ = service.get_by_id("nonexistent-id")

        assert exc_info.value.status_code == 404

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
        with pytest.raises(HTTPException) as exc_info:
            _ = service.create(family_data)

        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail.lower()

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
        with pytest.raises(HTTPException) as exc_info:
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
        with pytest.raises(HTTPException) as exc_info:
            service.delete(family_id)

        assert exc_info.value.status_code == 400
        assert "being used" in exc_info.value.detail.lower()

    def test_delete_family_not_found(self, db: Session) -> None:
        """Test deleting non-existent family raises 404"""
        repo = ModelFamilyRepository(db)
        service = ModelFamilyService(repo)

        with pytest.raises(HTTPException) as exc_info:
            service.delete("nonexistent-id")

        assert exc_info.value.status_code == 404
