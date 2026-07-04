"""Tests for ProviderService"""

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.provider import (
    DiscoveredModel,
    Provider,
    ProviderRepository,
    ProviderService,
    ProviderType,
)
from src.provider.model_cache import ModelListCache


class TestProviderService:
    """Test suite for ProviderService"""

    def test_list_all(self, db: Session) -> None:
        """Test listing all providers"""
        provider1 = Provider(name="OpenAI", provider_type=ProviderType.OPENAI)
        provider2 = Provider(name="Anthropic", provider_type=ProviderType.ANTHROPIC)
        db.add_all([provider1, provider2])
        db.commit()

        repo = ProviderRepository(db)
        service = ProviderService(repo)
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

        repo = ProviderRepository(db)
        service = ProviderService(repo)
        result = service.get_by_id(provider.id)

        assert result.id == provider.id
        assert result.name == "OpenAI"

    def test_get_by_id_not_found(self, db: Session) -> None:
        """Test getting a provider that doesn't exist raises 404"""
        repo = ProviderRepository(db)
        service = ProviderService(repo)

        with pytest.raises(HTTPException) as exc_info:
            _ = service.get_by_id("nonexistent-id")

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    def test_create_provider_success(self, db: Session) -> None:
        """Test creating a provider successfully"""
        repo = ProviderRepository(db)
        service = ProviderService(repo)

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
        # Create first provider
        provider1 = Provider(name="OpenAI", provider_type=ProviderType.OPENAI)
        db.add(provider1)
        db.commit()

        # Try to create duplicate
        repo = ProviderRepository(db)
        service = ProviderService(repo)
        with pytest.raises(HTTPException) as exc_info:
            _ = service.create(
                name="OpenAI",
                provider_type=ProviderType.ANTHROPIC,
            )

        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail.lower()

    def test_create_provider_minimal(self, db: Session) -> None:
        """Test creating a CUSTOM provider with api_key_env_var"""
        repo = ProviderRepository(db)
        service = ProviderService(repo)

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

        repo = ProviderRepository(db)
        service = ProviderService(repo)
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

        repo = ProviderRepository(db)
        service = ProviderService(repo)
        updated = service.update(provider.id, name="OpenAI Updated")

        assert updated.name == "OpenAI Updated"  # Changed
        assert updated.provider_type == ProviderType.OPENAI  # Unchanged
        assert updated.base_url == "https://api.openai.com"  # Unchanged

    def test_update_provider_not_found(self, db: Session) -> None:
        """Test updating non-existent provider raises 404"""
        repo = ProviderRepository(db)
        service = ProviderService(repo)

        with pytest.raises(HTTPException) as exc_info:
            _ = service.update("nonexistent-id", name="New Name")

        assert exc_info.value.status_code == 404

    def test_delete_provider_success(self, db: Session) -> None:
        """Test that deleting a provider raises NotImplementedError"""
        provider = Provider(name="OpenAI", provider_type=ProviderType.OPENAI)
        db.add(provider)
        db.commit()
        db.refresh(provider)
        provider_id = provider.id

        repo = ProviderRepository(db)
        service = ProviderService(repo)

        # Verify provider deletion is not allowed
        with pytest.raises(NotImplementedError) as exc_info:
            service.delete(provider_id)

        assert "cannot be deleted" in str(exc_info.value).lower()
        assert "update_flags" in str(exc_info.value).lower()

    def test_delete_provider_not_found(self, db: Session) -> None:
        """Test that deleting non-existent provider raises NotImplementedError"""
        repo = ProviderRepository(db)
        service = ProviderService(repo)

        # Even for non-existent providers, deletion should be blocked
        with pytest.raises(NotImplementedError) as exc_info:
            service.delete("nonexistent-id")

        assert "cannot be deleted" in str(exc_info.value).lower()


class _FakeDiscoveryClient:
    """Stand-in for OllamaDiscoveryClient/LMStudioDiscoveryClient in service tests."""

    def __init__(self, models: list[DiscoveredModel] | None = None, error: Exception | None = None):
        self.models = models or []
        self.error = error
        self.list_calls = 0
        self.load_calls: list[str] = []
        self.unload_calls: list[str] = []

    def list_models(self, base_url: str, api_key: str | None = None) -> list[DiscoveredModel]:
        self.list_calls += 1
        if self.error:
            raise self.error
        return self.models

    def load_model(self, base_url: str, identifier: str) -> None:
        if self.error:
            raise self.error
        self.load_calls.append(identifier)

    def unload_model(self, base_url: str, identifier: str) -> None:
        if self.error:
            raise self.error
        self.unload_calls.append(identifier)

    def delete_model(self, base_url: str, identifier: str) -> None:
        if self.error:
            raise self.error


class TestProviderServiceDiscovery:
    """Test suite for ProviderService model discovery/load/unload/cache logic"""

    def _make_ollama_provider(self, db: Session) -> Provider:
        provider = Provider(
            name="Ollama", provider_type=ProviderType.OLLAMA, base_url="http://localhost:11434"
        )
        db.add(provider)
        db.commit()
        db.refresh(provider)
        return provider

    def test_list_available_models_unsupported_provider_type(
        self, db: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = Provider(name="OpenAI", provider_type=ProviderType.OPENAI)
        db.add(provider)
        db.commit()
        db.refresh(provider)

        import src.provider.service
        monkeypatch.setattr(src.provider.service, "get_discovery_client", lambda x: None)

        service = ProviderService(ProviderRepository(db))
        with pytest.raises(HTTPException) as exc_info:
            service.list_available_models(provider.id)

        assert exc_info.value.status_code == 400

    def test_list_available_models_live_fetch_then_cache_hit(
        self, db: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = self._make_ollama_provider(db)
        fake_client = _FakeDiscoveryClient(
            models=[
                DiscoveredModel(identifier="llama3:8b", display_name="llama3:8b", state="loaded")
            ]
        )
        monkeypatch.setattr("src.provider.service.get_discovery_client", lambda _t: fake_client)

        service = ProviderService(ProviderRepository(db))

        first = service.list_available_models(provider.id)
        assert first.from_cache is False
        assert first.last_synced_at is not None
        assert fake_client.list_calls == 1

        second = service.list_available_models(provider.id)
        assert second.from_cache is True
        assert fake_client.list_calls == 1  # served from cache, no second live call

    def test_sync_models_bypasses_cache(self, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
        provider = self._make_ollama_provider(db)
        fake_client = _FakeDiscoveryClient(models=[])
        monkeypatch.setattr("src.provider.service.get_discovery_client", lambda _t: fake_client)

        service = ProviderService(ProviderRepository(db))
        service.list_available_models(provider.id)
        assert fake_client.list_calls == 1

        result = service.sync_models(provider.id)
        assert result.from_cache is False
        assert fake_client.list_calls == 2

    def test_discovery_cache_disabled_setting(
        self, db: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from src.core.config import settings

        provider = self._make_ollama_provider(db)
        fake_client = _FakeDiscoveryClient(models=[])
        monkeypatch.setattr("src.provider.service.get_discovery_client", lambda _t: fake_client)
        monkeypatch.setattr(settings.discovery_cache, "enabled", False)

        service = ProviderService(ProviderRepository(db))
        service.list_available_models(provider.id)
        service.list_available_models(provider.id)
        assert fake_client.list_calls == 2

    def test_list_available_models_unreachable_returns_502(
        self, db: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = self._make_ollama_provider(db)
        fake_client = _FakeDiscoveryClient(error=httpx.ConnectError("connection refused"))
        monkeypatch.setattr("src.provider.service.get_discovery_client", lambda _t: fake_client)

        service = ProviderService(ProviderRepository(db))
        with pytest.raises(HTTPException) as exc_info:
            service.list_available_models(provider.id)

        assert exc_info.value.status_code == 502

    def test_load_model_invalidates_cache(
        self, db: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = self._make_ollama_provider(db)
        fake_client = _FakeDiscoveryClient(models=[])
        monkeypatch.setattr("src.provider.service.get_discovery_client", lambda _t: fake_client)

        service = ProviderService(ProviderRepository(db))
        service.list_available_models(provider.id)
        assert fake_client.list_calls == 1

        result = service.load_model(provider.id, "llama3:8b")
        assert result.action == "loaded"
        assert fake_client.load_calls == ["llama3:8b"]

        service.list_available_models(provider.id)
        assert fake_client.list_calls == 2  # cache was invalidated by the load

    def test_unload_model(self, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
        provider = self._make_ollama_provider(db)
        fake_client = _FakeDiscoveryClient(models=[])
        monkeypatch.setattr("src.provider.service.get_discovery_client", lambda _t: fake_client)

        service = ProviderService(ProviderRepository(db))
        result = service.unload_model(provider.id, "llama3:8b")

        assert result.action == "unloaded"
        assert fake_client.unload_calls == ["llama3:8b"]

    def test_model_cache_is_isolated_per_service_instance_by_default(self, db: Session) -> None:
        """Two ProviderService(repo) calls without an explicit cache get independent caches."""
        service_a = ProviderService(ProviderRepository(db))
        service_b = ProviderService(ProviderRepository(db))
        assert service_a.model_cache is not service_b.model_cache

    def test_model_cache_can_be_shared_explicitly(self, db: Session) -> None:
        shared_cache = ModelListCache()
        service_a = ProviderService(ProviderRepository(db), shared_cache)
        service_b = ProviderService(ProviderRepository(db), shared_cache)
        assert service_a.model_cache is service_b.model_cache
