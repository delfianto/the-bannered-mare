"""Tests for ModelService"""

from typing import Any
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.chat_session import Chat, ChatRepository
from src.model import Model, ModelRepository, ModelService
from src.model_family import ModelFamily, ModelFamilyRepository
from src.provider import Provider, ProviderRepository, ProviderType


class TestModelService:
    """Test suite for ModelService"""

    def test_list_all(self, db: Session, sample_provider: Any, sample_family: Any) -> None:
        """Test listing all models"""
        model1 = Model(
            name="GPT-4",
            provider_id=sample_provider.id,
            model_identifier="gpt-4",
            model_family_id=sample_family.id,
        )
        model2 = Model(
            name="GPT-3.5",
            provider_id=sample_provider.id,
            model_identifier="gpt-3.5-turbo",
            model_family_id=sample_family.id,
        )
        db.add_all([model1, model2])
        db.commit()

        repo = ModelRepository(db)
        provider_repo = ProviderRepository(db)
        family_repo = ModelFamilyRepository(db)
        chat_repo = ChatRepository(db)
        service = ModelService(repo, provider_repo, family_repo, chat_repo)
        models = service.list_all()

        assert len(models) == 2
        assert any(m.name == "GPT-4" for m in models)
        assert any(m.name == "GPT-3.5" for m in models)

    def test_get_by_id_success(self, db: Session, sample_model: Any) -> None:
        """Test getting a model by ID successfully"""
        repo = ModelRepository(db)
        provider_repo = ProviderRepository(db)
        family_repo = ModelFamilyRepository(db)
        chat_repo = ChatRepository(db)
        service = ModelService(repo, provider_repo, family_repo, chat_repo)
        result = service.get_by_id(sample_model.id)

        assert result.id == sample_model.id
        assert result.name == sample_model.name
        assert result.model_identifier == sample_model.model_identifier

    def test_get_by_id_not_found(self, db: Session) -> None:
        """Test getting a model that doesn't exist raises 404"""
        repo = ModelRepository(db)
        provider_repo = ProviderRepository(db)
        family_repo = ModelFamilyRepository(db)
        chat_repo = ChatRepository(db)
        service = ModelService(repo, provider_repo, family_repo, chat_repo)

        with pytest.raises(HTTPException) as exc_info:
            _ = service.get_by_id("nonexistent-id")

        assert exc_info.value.status_code == 404

    def test_create_model_success(
        self, db: Session, sample_provider: Any, sample_family: Any
    ) -> None:
        """Test creating a model successfully"""
        repo = ModelRepository(db)
        provider_repo = ProviderRepository(db)
        family_repo = ModelFamilyRepository(db)
        chat_repo = ChatRepository(db)
        service = ModelService(repo, provider_repo, family_repo, chat_repo)
        # Mock has_api_key to return True for testing
        with patch.object(Provider, "has_api_key", return_value=True):
            model = service.create(
                name="New GPT-4",
                provider_id=sample_provider.id,
                model_identifier="gpt-4-new",
                model_family_id=sample_family.id,
            )

        assert model.name == "New GPT-4"
        assert model.provider_id == sample_provider.id
        assert model.model_identifier == "gpt-4-new"
        assert model.model_family_id == sample_family.id

    def test_create_model_provider_not_found(self, db: Session) -> None:
        """Test creating a model with non-existent provider raises error"""
        repo = ModelRepository(db)
        provider_repo = ProviderRepository(db)
        family_repo = ModelFamilyRepository(db)
        chat_repo = ChatRepository(db)
        service = ModelService(repo, provider_repo, family_repo, chat_repo)

        with pytest.raises(HTTPException) as exc_info:
            _ = service.create(
                name="GPT-4",
                provider_id="nonexistent-provider",
                model_identifier="gpt-4",
                model_family_id="any-family-id",
            )

        assert exc_info.value.status_code == 404
        assert "Provider" in exc_info.value.detail

    def test_create_model_minimal(
        self, db: Session, sample_provider: Any, sample_family: Any
    ) -> None:
        """Test creating a model with minimal fields"""
        repo = ModelRepository(db)
        provider_repo = ProviderRepository(db)
        family_repo = ModelFamilyRepository(db)
        chat_repo = ChatRepository(db)
        service = ModelService(repo, provider_repo, family_repo, chat_repo)
        # Mock has_api_key to return True for testing
        with patch.object(Provider, "has_api_key", return_value=True):
            model = service.create(
                name="Minimal Model",
                provider_id=sample_provider.id,
                model_identifier="gpt-4-min",
                model_family_id=sample_family.id,
            )

        assert model.name == "Minimal Model"
        assert model.model_family_id == sample_family.id
        assert model.template_id is None
        assert model.parameters.get("temperature") is None

    def test_update_model_all_fields(self, db: Session, sample_model: Any) -> None:
        """Test updating all model fields"""
        provider2 = Provider(name="Anthropic", provider_type=ProviderType.ANTHROPIC)
        family2 = ModelFamily(
            name="Claude",
            family_identifier="test.claude",
            parameters={"temperature": {"supported": True}},
        )
        db.add_all([provider2, family2])
        db.commit()

        repo = ModelRepository(db)
        provider_repo = ProviderRepository(db)
        family_repo = ModelFamilyRepository(db)
        chat_repo = ChatRepository(db)
        service = ModelService(repo, provider_repo, family_repo, chat_repo)
        updated = service.update(
            sample_model.id,
            name="Claude 3",
            provider_id=provider2.id,
            model_identifier="claude-3-opus",
            model_family_id=family2.id,
        )

        assert updated.name == "Claude 3"
        assert updated.provider_id == provider2.id
        assert updated.model_identifier == "claude-3-opus"
        assert updated.model_family_id == family2.id

    def test_update_model_provider_not_found(self, db: Session, sample_model: Any) -> None:
        """Test updating model with non-existent provider raises error"""
        repo = ModelRepository(db)
        provider_repo = ProviderRepository(db)
        family_repo = ModelFamilyRepository(db)
        chat_repo = ChatRepository(db)
        service = ModelService(repo, provider_repo, family_repo, chat_repo)
        with pytest.raises(HTTPException) as exc_info:
            _ = service.update(sample_model.id, provider_id="nonexistent-provider")

        assert exc_info.value.status_code == 404
        assert "Provider" in exc_info.value.detail

    def test_delete_model_success(self, db: Session, sample_model: Any) -> None:
        """Test deleting a model successfully"""
        model_id = sample_model.id

        repo = ModelRepository(db)
        provider_repo = ProviderRepository(db)
        family_repo = ModelFamilyRepository(db)
        chat_repo = ChatRepository(db)
        service = ModelService(repo, provider_repo, family_repo, chat_repo)
        service.delete(model_id)

        # Verify model is deleted
        deleted = db.query(Model).filter(Model.id == model_id).first()
        assert deleted is None

    def test_delete_model_in_use(
        self, db: Session, sample_model: Any, sample_character: Any
    ) -> None:
        """Test deleting a model that is in use succeeds (and unlinks)"""
        chat = Chat(title="Test Chat", character_id=sample_character.id, model_id=sample_model.id)
        db.add(chat)
        db.commit()
        db.refresh(chat)

        # Try to delete model
        repo = ModelRepository(db)
        provider_repo = ProviderRepository(db)
        family_repo = ModelFamilyRepository(db)
        chat_repo = ChatRepository(db)
        service = ModelService(repo, provider_repo, family_repo, chat_repo)

        # Should NOT raise exception now
        service.delete(sample_model.id)

        # Verify model is deleted
        deleted = db.query(Model).filter(Model.id == sample_model.id).first()
        assert deleted is None

        # Verify chat still exists and model_id is None
        db.expire_all()
        updated_chat = db.query(Chat).filter(Chat.id == chat.id).first()
        assert updated_chat is not None
        assert updated_chat.model_id is None

    def test_delete_model_not_found(self, db: Session) -> None:
        """Test deleting non-existent model raises 404"""
        repo = ModelRepository(db)
        provider_repo = ProviderRepository(db)
        family_repo = ModelFamilyRepository(db)
        chat_repo = ChatRepository(db)
        service = ModelService(repo, provider_repo, family_repo, chat_repo)

        with pytest.raises(HTTPException) as exc_info:
            service.delete("nonexistent-id")

        assert exc_info.value.status_code == 404
