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

    def test_list_paginated_orders_by_name_case_insensitive(
        self, db: Session, sample_provider: Any, sample_family: Any
    ) -> None:
        """list_paginated returns models alphabetically by name, ignoring case."""
        # Mixed case whose case-insensitive order ("apex, banana, Mango, Zeta")
        # differs from raw ASCII order ("Mango, Zeta, apex, banana").
        for i, name in enumerate(["Zeta", "apex", "Mango", "banana"]):
            db.add(
                Model(
                    name=name,
                    provider_id=sample_provider.id,
                    model_identifier=f"id-{i}",
                    model_family_id=sample_family.id,
                )
            )
        db.commit()

        repo = ModelRepository(db)
        provider_repo = ProviderRepository(db)
        family_repo = ModelFamilyRepository(db)
        chat_repo = ChatRepository(db)
        service = ModelService(repo, provider_repo, family_repo, chat_repo)

        models, total = service.list_paginated(limit=10, offset=0)

        assert total == 4
        assert [m.name for m in models] == ["apex", "banana", "Mango", "Zeta"]

    def test_list_paginated_filters_by_model_family(
        self, db: Session, sample_provider: Any, sample_family: Any
    ) -> None:
        """The model_family_id filter returns only that family's models."""
        other = ModelFamily(name="Other Family", family_identifier="test.other-family")
        db.add(other)
        db.commit()
        db.refresh(other)
        db.add_all(
            [
                Model(
                    name="In Family",
                    provider_id=sample_provider.id,
                    model_identifier="in-fam",
                    model_family_id=sample_family.id,
                ),
                Model(
                    name="Other",
                    provider_id=sample_provider.id,
                    model_identifier="other",
                    model_family_id=other.id,
                ),
            ]
        )
        db.commit()

        repo = ModelRepository(db)
        provider_repo = ProviderRepository(db)
        family_repo = ModelFamilyRepository(db)
        chat_repo = ChatRepository(db)
        service = ModelService(repo, provider_repo, family_repo, chat_repo)

        models, total = service.list_paginated(filters={"model_family_id": sample_family.id})

        assert total == 1
        assert [m.name for m in models] == ["In Family"]

    def test_routing_derived_identity_properties(
        self, db: Session, sample_provider: Any, sample_family: Any
    ) -> None:
        """active_identifier / effective_provider_id follow the routing override:
        a native model uses its own identifier + provider, a routed one the
        override's identifier + provider."""
        native = Model(
            name="Native",
            provider_id=sample_provider.id,
            model_identifier="gpt-4o",
            model_family_id=sample_family.id,
        )
        routed = Model(
            name="Routed",
            provider_id=sample_provider.id,
            model_identifier="deepseek-v4-flash",
            model_family_id=sample_family.id,
            routing_provider_id=sample_provider.id,
            routing_identifier="deepseek/deepseek-v4-flash",
        )
        db.add_all([native, routed])
        db.commit()

        assert native.active_identifier == "gpt-4o"
        assert native.effective_provider_id == sample_provider.id
        assert routed.active_identifier == "deepseek/deepseek-v4-flash"
        assert routed.effective_provider_id == sample_provider.id

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
            provider_types=["anthropic"],
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

    def test_create_rejects_provider_type_not_in_family(self, db: Session) -> None:
        """A family that can't run on the chosen provider type is a 400."""
        provider = Provider(name="Local LM Studio", provider_type=ProviderType.LMSTUDIO)
        family = ModelFamily(
            name="Ollama-only Fam",
            family_identifier="test/ollama-only",
            provider_types=["ollama"],
        )
        db.add_all([provider, family])
        db.commit()

        service = ModelService(
            ModelRepository(db),
            ProviderRepository(db),
            ModelFamilyRepository(db),
            ChatRepository(db),
        )
        with pytest.raises(HTTPException) as exc:
            service.create(
                name="X",
                provider_id=provider.id,
                model_identifier="x",
                model_family_id=family.id,
            )
        assert exc.value.status_code == 400
        assert "cannot serve" in exc.value.detail

    def test_create_allows_provider_type_in_family(self, db: Session) -> None:
        """LM Studio is allowed once the family lists it."""
        provider = Provider(name="Local LM Studio", provider_type=ProviderType.LMSTUDIO)
        family = ModelFamily(
            name="Local Fam",
            family_identifier="test/local",
            provider_types=["ollama", "lmstudio"],
        )
        db.add_all([provider, family])
        db.commit()

        service = ModelService(
            ModelRepository(db),
            ProviderRepository(db),
            ModelFamilyRepository(db),
            ChatRepository(db),
        )
        created = service.create(
            name="X", provider_id=provider.id, model_identifier="x", model_family_id=family.id
        )
        assert created.id

    def test_update_rejects_family_change_incompatible_with_provider(self, db: Session) -> None:
        """Switching to a family the current provider can't serve is a 400."""
        provider = Provider(name="Local LM Studio", provider_type=ProviderType.LMSTUDIO)
        ok_family = ModelFamily(
            name="Local Fam2", family_identifier="test/local2", provider_types=["lmstudio"]
        )
        cloud_family = ModelFamily(
            name="Cloud Fam", family_identifier="test/cloud", provider_types=["anthropic"]
        )
        db.add_all([provider, ok_family, cloud_family])
        db.commit()
        service = ModelService(
            ModelRepository(db),
            ProviderRepository(db),
            ModelFamilyRepository(db),
            ChatRepository(db),
        )
        model = service.create(
            name="X", provider_id=provider.id, model_identifier="x", model_family_id=ok_family.id
        )
        with pytest.raises(HTTPException) as exc:
            service.update(model.id, model_family_id=cloud_family.id)
        assert exc.value.status_code == 400

    def test_update_rejects_provider_change_incompatible_with_family(self, db: Session) -> None:
        """Switching to a provider the current family can't run on is a 400."""
        lmstudio = Provider(name="Local LM Studio", provider_type=ProviderType.LMSTUDIO)
        anthropic = Provider(name="Anthropic", provider_type=ProviderType.ANTHROPIC)
        family = ModelFamily(
            name="Local Fam3", family_identifier="test/local3", provider_types=["lmstudio"]
        )
        db.add_all([lmstudio, anthropic, family])
        db.commit()
        service = ModelService(
            ModelRepository(db),
            ProviderRepository(db),
            ModelFamilyRepository(db),
            ChatRepository(db),
        )
        model = service.create(
            name="X", provider_id=lmstudio.id, model_identifier="x", model_family_id=family.id
        )
        with pytest.raises(HTTPException) as exc:
            service.update(model.id, provider_id=anthropic.id)
        assert exc.value.status_code == 400
        assert "cannot serve" in exc.value.detail
