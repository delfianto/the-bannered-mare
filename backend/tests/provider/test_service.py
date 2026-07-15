"""Tests for ProviderService (provider entity CRUD).

Model discovery/cache/action behaviour lives in ``test_model_service.py`` and
the pure discovery filters in ``test_discovery_filters.py``.
"""

import pytest
from sqlalchemy.orm import Session
from src.core.exceptions import BanneredMareException, ConflictError
from src.provider import Provider, ProviderRepository, ProviderService, ProviderType


class TestProviderService:
    """Test suite for ProviderService"""

    def test_list_all(self, db: Session) -> None:
        """Test listing all providers"""
        provider1 = Provider(name="OpenAI", provider_type=ProviderType.OPENAI)
        provider2 = Provider(name="Anthropic", provider_type=ProviderType.ANTHROPIC)
        db.add_all([provider1, provider2])
        db.commit()

        service = ProviderService(ProviderRepository(db))
        providers = service.list_all()

        assert len(providers) == 2
        assert any(p.name == "OpenAI" for p in providers)
        assert any(p.name == "Anthropic" for p in providers)

    def test_get_by_id_success(self, db: Session) -> None:
        """Test getting a provider by ID successfully"""
        provider = Provider(name="OpenAI", provider_type=ProviderType.OPENAI)
        db.add(provider)
        db.commit()
        db.refresh(provider)

        service = ProviderService(ProviderRepository(db))
        result = service.get_by_id(provider.id)

        assert result.id == provider.id
        assert result.name == "OpenAI"

    def test_get_by_id_not_found(self, db: Session) -> None:
        """Test getting a provider that doesn't exist raises 404"""
        service = ProviderService(ProviderRepository(db))

        with pytest.raises(BanneredMareException) as exc_info:
            _ = service.get_by_id("nonexistent-id")

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.message.lower()

    def test_create_provider_success(self, db: Session) -> None:
        """Test creating a provider successfully"""
        service = ProviderService(ProviderRepository(db))

        provider = service.create(
            name="OpenAI",
            provider_type=ProviderType.OPENAI,
            base_url="https://api.openai.com",
        )

        assert provider.name == "OpenAI"
        assert provider.provider_type == ProviderType.OPENAI
        assert provider.base_url == "https://api.openai.com"
        assert provider.id is not None

    def test_create_provider_duplicate_name(self, db: Session) -> None:
        """Test creating a provider with duplicate name raises error"""
        provider1 = Provider(name="OpenAI", provider_type=ProviderType.OPENAI)
        db.add(provider1)
        db.commit()

        service = ProviderService(ProviderRepository(db))
        with pytest.raises(BanneredMareException) as exc_info:
            _ = service.create(
                name="OpenAI",
                provider_type=ProviderType.ANTHROPIC,
            )

        assert exc_info.value.status_code == 409
        assert "already exists" in exc_info.value.message.lower()

    def test_create_provider_minimal(self, db: Session) -> None:
        """Test creating a CUSTOM provider with api_key_env_var"""
        service = ProviderService(ProviderRepository(db))

        provider = service.create(
            name="Custom Provider",
            provider_type=ProviderType.CUSTOM,
            api_key_env_var="MY_CUSTOM_API_KEY",
            base_url="https://custom.api.com",
        )

        assert provider.name == "Custom Provider"
        assert provider.provider_type == ProviderType.CUSTOM
        assert provider.api_key_env_var == "MY_CUSTOM_API_KEY"
        assert provider.base_url == "https://custom.api.com"

    def test_update_provider_all_fields(self, db: Session) -> None:
        """Test updating custom provider fields"""
        provider = Provider(
            name="Custom Provider",
            provider_type=ProviderType.CUSTOM,
            api_key_env_var="OLD_API_KEY",
        )
        db.add(provider)
        db.commit()
        db.refresh(provider)

        service = ProviderService(ProviderRepository(db))
        updated = service.update(
            provider.id,
            name="Custom Provider Updated",
            api_key_env_var="NEW_API_KEY",
            base_url="https://custom.api.com",
        )

        assert updated.name == "Custom Provider Updated"
        assert updated.provider_type == ProviderType.CUSTOM
        assert updated.api_key_env_var == "NEW_API_KEY"
        assert updated.base_url == "https://custom.api.com"

    def test_update_provider_partial(self, db: Session) -> None:
        """Test updating only some provider fields"""
        provider = Provider(
            name="OpenAI",
            provider_type=ProviderType.OPENAI,
            base_url="https://api.openai.com",
        )
        db.add(provider)
        db.commit()
        db.refresh(provider)

        service = ProviderService(ProviderRepository(db))
        updated = service.update(provider.id, name="OpenAI Updated")

        assert updated.name == "OpenAI Updated"  # Changed
        assert updated.provider_type == ProviderType.OPENAI  # Unchanged
        assert updated.base_url == "https://api.openai.com"  # Unchanged

    def test_update_provider_not_found(self, db: Session) -> None:
        """Test updating non-existent provider raises 404"""
        service = ProviderService(ProviderRepository(db))

        with pytest.raises(BanneredMareException) as exc_info:
            _ = service.update("nonexistent-id", name="New Name")

        assert exc_info.value.status_code == 404

    def test_delete_provider_success(self, db: Session) -> None:
        """Deleting a provider is blocked with a domain ConflictError (→ 409)."""
        provider = Provider(name="OpenAI", provider_type=ProviderType.OPENAI)
        db.add(provider)
        db.commit()
        db.refresh(provider)
        provider_id = provider.id

        service = ProviderService(ProviderRepository(db))

        with pytest.raises(ConflictError) as exc_info:
            service.delete(provider_id)

        assert exc_info.value.status_code == 409
        assert "cannot be deleted" in exc_info.value.message.lower()
        assert "update_flags" in exc_info.value.message.lower()

    def test_delete_provider_not_found(self, db: Session) -> None:
        """Even for non-existent providers, deletion is blocked with ConflictError."""
        service = ProviderService(ProviderRepository(db))

        with pytest.raises(ConflictError) as exc_info:
            service.delete("nonexistent-id")

        assert "cannot be deleted" in exc_info.value.message.lower()
