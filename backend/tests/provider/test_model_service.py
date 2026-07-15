"""Tests for ProviderModelService — discovery, caching, and runtime actions."""

import httpx
import pytest
from sqlalchemy.orm import Session
from src.core.exceptions import BanneredMareException, ProviderException
from src.provider import (
    DiscoveredModel,
    Provider,
    ProviderModelService,
    ProviderRepository,
    ProviderType,
)
from src.provider.model_cache import ModelListCache


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


class TestProviderModelService:
    """Test suite for ProviderModelService discovery/load/unload/cache logic"""

    def _make_ollama_provider(self, db: Session) -> Provider:
        provider = Provider(
            name="Ollama", provider_type=ProviderType.OLLAMA, base_url="http://localhost:11434"
        )
        db.add(provider)
        db.commit()
        db.refresh(provider)
        return provider

    def _make_cloud_provider(self, db: Session) -> Provider:
        # Cloud providers cache on read (large, stable catalogs, no live load-state).
        provider = Provider(
            name="OpenRouter",
            provider_type=ProviderType.OPENROUTER,
            base_url="https://openrouter.ai/api/v1",
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

        import src.provider.model_service

        monkeypatch.setattr(src.provider.model_service, "get_discovery_client", lambda x: None)

        service = ProviderModelService(ProviderRepository(db), ModelListCache())
        with pytest.raises(BanneredMareException) as exc_info:
            service.list_available_models(provider.id)

        assert exc_info.value.status_code == 422

    def test_list_available_models_live_fetch_then_cache_hit(
        self, db: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Cloud provider: second read is served from cache.
        provider = self._make_cloud_provider(db)
        fake_client = _FakeDiscoveryClient(
            models=[
                DiscoveredModel(identifier="openai/gpt-5", display_name="GPT-5", state="loaded")
            ]
        )
        monkeypatch.setattr(
            "src.provider.model_service.get_discovery_client", lambda _t: fake_client
        )

        service = ProviderModelService(ProviderRepository(db), ModelListCache())

        first = service.list_available_models(provider.id)
        assert first.from_cache is False
        assert first.last_synced_at is not None
        assert fake_client.list_calls == 1

        second = service.list_available_models(provider.id)
        assert second.from_cache is True
        assert fake_client.list_calls == 1  # served from cache, no second live call

    def test_local_provider_always_fetches_fresh(
        self, db: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Ollama/LM Studio load-state is live, so reads never serve a stale cache."""
        provider = self._make_ollama_provider(db)
        fake_client = _FakeDiscoveryClient(
            models=[
                DiscoveredModel(identifier="llama3:8b", display_name="llama3:8b", state="loaded")
            ]
        )
        monkeypatch.setattr(
            "src.provider.model_service.get_discovery_client", lambda _t: fake_client
        )

        service = ProviderModelService(ProviderRepository(db), ModelListCache())
        first = service.list_available_models(provider.id)
        second = service.list_available_models(provider.id)

        assert first.from_cache is False
        assert second.from_cache is False  # not cached — fetched live again
        assert fake_client.list_calls == 2

    def test_local_provider_falls_back_to_cache_when_unreachable(
        self, db: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A briefly-down local box serves the last-known list instead of erroring."""
        provider = self._make_ollama_provider(db)
        fake_client = _FakeDiscoveryClient(
            models=[
                DiscoveredModel(identifier="llama3:8b", display_name="llama3:8b", state="loaded")
            ]
        )
        monkeypatch.setattr(
            "src.provider.model_service.get_discovery_client", lambda _t: fake_client
        )

        service = ProviderModelService(ProviderRepository(db), ModelListCache())
        service.list_available_models(provider.id)  # populates the cache

        fake_client.error = httpx.ConnectError("connection refused")  # box goes down
        result = service.list_available_models(provider.id)

        assert result.from_cache is True
        assert [m.identifier for m in result.models] == ["llama3:8b"]

    def test_sync_models_bypasses_cache(self, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
        provider = self._make_ollama_provider(db)
        fake_client = _FakeDiscoveryClient(models=[])
        monkeypatch.setattr(
            "src.provider.model_service.get_discovery_client", lambda _t: fake_client
        )

        service = ProviderModelService(ProviderRepository(db), ModelListCache())
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
        monkeypatch.setattr(
            "src.provider.model_service.get_discovery_client", lambda _t: fake_client
        )
        monkeypatch.setattr(settings.discovery_cache, "enabled", False)

        service = ProviderModelService(ProviderRepository(db), ModelListCache())
        service.list_available_models(provider.id)
        service.list_available_models(provider.id)
        assert fake_client.list_calls == 2

    def test_list_available_models_unreachable_returns_502(
        self, db: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = self._make_ollama_provider(db)
        fake_client = _FakeDiscoveryClient(error=httpx.ConnectError("connection refused"))
        monkeypatch.setattr(
            "src.provider.model_service.get_discovery_client", lambda _t: fake_client
        )

        service = ProviderModelService(ProviderRepository(db), ModelListCache())
        # ProviderException maps to HTTP 502 via the global handler.
        with pytest.raises(ProviderException):
            service.list_available_models(provider.id)

    def test_load_model_invalidates_cache(
        self, db: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = self._make_ollama_provider(db)
        fake_client = _FakeDiscoveryClient(models=[])
        monkeypatch.setattr(
            "src.provider.model_service.get_discovery_client", lambda _t: fake_client
        )

        service = ProviderModelService(ProviderRepository(db), ModelListCache())
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
        monkeypatch.setattr(
            "src.provider.model_service.get_discovery_client", lambda _t: fake_client
        )

        service = ProviderModelService(ProviderRepository(db), ModelListCache())
        result = service.unload_model(provider.id, "llama3:8b")

        assert result.action == "unloaded"
        assert fake_client.unload_calls == ["llama3:8b"]

    def test_model_cache_can_be_shared_explicitly(self, db: Session) -> None:
        shared_cache = ModelListCache()
        service_a = ProviderModelService(ProviderRepository(db), shared_cache)
        service_b = ProviderModelService(ProviderRepository(db), shared_cache)
        assert service_a.model_cache is service_b.model_cache

    def test_list_available_models_applies_allow_list(
        self, db: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = self._make_ollama_provider(db)
        provider.allowed_models = ["keep:1"]
        db.commit()
        fake_client = _FakeDiscoveryClient(
            models=[
                DiscoveredModel(identifier="keep:1", display_name="Keep One", state="loaded"),
                DiscoveredModel(identifier="drop:2", display_name="Drop Two", state="loaded"),
            ]
        )
        monkeypatch.setattr(
            "src.provider.model_service.get_discovery_client", lambda _t: fake_client
        )

        service = ProviderModelService(ProviderRepository(db), ModelListCache())
        result = service.list_available_models(provider.id)

        assert [m.identifier for m in result.models] == ["keep:1"]

    def test_list_available_models_empty_allow_list_returns_all(
        self, db: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = self._make_ollama_provider(db)
        fake_client = _FakeDiscoveryClient(
            models=[
                DiscoveredModel(identifier="a:1", display_name="A", state="loaded"),
                DiscoveredModel(identifier="b:2", display_name="B", state="loaded"),
            ]
        )
        monkeypatch.setattr(
            "src.provider.model_service.get_discovery_client", lambda _t: fake_client
        )

        service = ProviderModelService(ProviderRepository(db), ModelListCache())
        result = service.list_available_models(provider.id)

        assert {m.identifier for m in result.models} == {"a:1", "b:2"}

    def test_search_models_substring_ignores_allow_list(
        self, db: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = self._make_ollama_provider(db)
        # A narrow allow-list must NOT constrain search — you search to expand it.
        provider.allowed_models = ["gpt-4o"]
        db.commit()
        fake_client = _FakeDiscoveryClient(
            models=[
                DiscoveredModel(identifier="gpt-4o", display_name="GPT-4o", state="loaded"),
                DiscoveredModel(
                    identifier="gpt-4o-mini", display_name="GPT-4o mini", state="loaded"
                ),
                DiscoveredModel(identifier="claude-3", display_name="Claude 3", state="loaded"),
            ]
        )
        monkeypatch.setattr(
            "src.provider.model_service.get_discovery_client", lambda _t: fake_client
        )

        service = ProviderModelService(ProviderRepository(db), ModelListCache())
        result = service.search_models(provider.id, "GPT-4O")  # case-insensitive

        assert [m.identifier for m in result.models] == ["gpt-4o", "gpt-4o-mini"]
        assert result.query == "GPT-4O"

    def test_search_models_matches_display_name(
        self, db: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = self._make_ollama_provider(db)
        fake_client = _FakeDiscoveryClient(
            models=[
                DiscoveredModel(identifier="x:1", display_name="Wizard LM", state="loaded"),
                DiscoveredModel(identifier="y:2", display_name="Other", state="loaded"),
            ]
        )
        monkeypatch.setattr(
            "src.provider.model_service.get_discovery_client", lambda _t: fake_client
        )

        service = ProviderModelService(ProviderRepository(db), ModelListCache())
        result = service.search_models(provider.id, "wizard")

        assert [m.identifier for m in result.models] == ["x:1"]

    def test_search_models_caps_results(self, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
        provider = self._make_ollama_provider(db)
        many = [
            DiscoveredModel(
                identifier=f"model-{i:03d}", display_name=f"model-{i:03d}", state="loaded"
            )
            for i in range(120)
        ]
        fake_client = _FakeDiscoveryClient(models=many)
        monkeypatch.setattr(
            "src.provider.model_service.get_discovery_client", lambda _t: fake_client
        )

        service = ProviderModelService(ProviderRepository(db), ModelListCache())
        result = service.search_models(provider.id, "model-")

        assert len(result.models) == 50

    def test_set_allowed_models_persists_and_normalizes(
        self, db: Session, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = self._make_ollama_provider(db)
        fake_client = _FakeDiscoveryClient(
            models=[
                DiscoveredModel(identifier="keep:1", display_name="Keep One", state="loaded"),
                DiscoveredModel(identifier="drop:2", display_name="Drop Two", state="loaded"),
            ]
        )
        monkeypatch.setattr(
            "src.provider.model_service.get_discovery_client", lambda _t: fake_client
        )

        service = ProviderModelService(ProviderRepository(db), ModelListCache())
        result = service.set_allowed_models(provider.id, ["keep:1", "keep:1", "  ", "keep:1"])

        db.refresh(provider)
        assert provider.allowed_models == ["keep:1"]  # deduped, blanks dropped, persisted
        assert [m.identifier for m in result.models] == ["keep:1"]  # response already filtered
