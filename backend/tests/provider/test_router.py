"""Tests for provider router"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.model import ModelRegistry, ModelRoute
from src.model_family import ModelFamily
from src.provider import DiscoveredModel, Provider, ProviderType


def test_list_providers_empty(client: TestClient) -> None:
    """Test listing providers"""
    # Note: seed_default_providers runs during lifespan, so it's not actually empty
    response = client.get("/api/providers")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_create_provider(client: TestClient) -> None:
    """Test creating a provider"""
    payload = {
        "name": "Custom",
        "provider_type": "custom",
        "base_url": "https://api.example.com",
        "api_key_env_var": "CUSTOM_KEY",
    }
    response = client.post("/api/providers", json=payload)
    assert response.status_code == 201
    assert response.json()["name"] == "Custom"


def test_get_provider(client: TestClient, db: Session) -> None:
    """Test getting a provider by ID"""
    provider = Provider(name="GetMe", provider_type=ProviderType.OPENAI)
    db.add(provider)
    db.commit()
    db.refresh(provider)

    response = client.get(f"/api/providers/{provider.id}")
    assert response.status_code == 200
    assert response.json()["name"] == "GetMe"


def _make_ollama_provider(db: Session) -> Provider:
    provider = Provider(
        name="Ollama", provider_type=ProviderType.OLLAMA, base_url="http://localhost:11434"
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


def test_list_available_models_unsupported_provider_type(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cloud providers don't support model auto-detection when mock returned client is None"""
    provider = Provider(name="OpenAI", provider_type=ProviderType.OPENAI)
    db.add(provider)
    db.commit()
    db.refresh(provider)

    monkeypatch.setattr(
        "src.provider.service.get_discovery_client",
        lambda _t: None,
    )

    response = client.get(f"/api/providers/{provider.id}/models/available")
    assert response.status_code == 400


def test_list_available_models(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = _make_ollama_provider(db)
    models = [DiscoveredModel(identifier="llama3:8b", display_name="llama3:8b", state="loaded")]
    monkeypatch.setattr(
        "src.provider.service.get_discovery_client",
        lambda _t: type("_C", (), {"list_models": lambda self, base_url, api_key=None: models})(),
    )

    response = client.get(f"/api/providers/{provider.id}/models/available")
    assert response.status_code == 200
    data = response.json()
    assert data["provider_id"] == provider.id
    assert data["models"][0]["identifier"] == "llama3:8b"
    assert data["from_cache"] is False


def test_sync_provider_models(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = _make_ollama_provider(db)
    monkeypatch.setattr(
        "src.provider.service.get_discovery_client",
        lambda _t: type("_C", (), {"list_models": lambda self, base_url, api_key=None: []})(),
    )

    response = client.post(f"/api/providers/{provider.id}/models/sync")
    assert response.status_code == 200
    assert response.json()["from_cache"] is False


def test_load_provider_model(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = _make_ollama_provider(db)
    calls: list[str] = []
    monkeypatch.setattr(
        "src.provider.service.get_discovery_client",
        lambda _t: type(
            "_C", (), {"load_model": lambda self, base_url, identifier: calls.append(identifier)}
        )(),
    )

    response = client.post(
        f"/api/providers/{provider.id}/models/load", json={"model_identifier": "llama3:8b"}
    )
    assert response.status_code == 200
    assert response.json() == {"model_identifier": "llama3:8b", "action": "loaded"}
    assert calls == ["llama3:8b"]


def test_unload_provider_model(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = _make_ollama_provider(db)
    calls: list[str] = []
    monkeypatch.setattr(
        "src.provider.service.get_discovery_client",
        lambda _t: type(
            "_C",
            (),
            {"unload_model": lambda self, base_url, identifier: calls.append(identifier)},
        )(),
    )

    response = client.post(
        f"/api/providers/{provider.id}/models/unload", json={"model_identifier": "llama3:8b"}
    )
    assert response.status_code == 200
    assert response.json() == {"model_identifier": "llama3:8b", "action": "unloaded"}
    assert calls == ["llama3:8b"]


def test_search_provider_models(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = _make_ollama_provider(db)
    models = [
        DiscoveredModel(identifier="gpt-4o", display_name="GPT-4o", state="loaded"),
        DiscoveredModel(identifier="gpt-4o-mini", display_name="GPT-4o mini", state="loaded"),
        DiscoveredModel(identifier="claude-3", display_name="Claude 3", state="loaded"),
    ]
    monkeypatch.setattr(
        "src.provider.service.get_discovery_client",
        lambda _t: type("_C", (), {"list_models": lambda self, base_url, api_key=None: models})(),
    )

    response = client.get(f"/api/providers/{provider.id}/models/search", params={"q": "gpt-4o"})
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "gpt-4o"
    assert [m["identifier"] for m in data["models"]] == ["gpt-4o", "gpt-4o-mini"]


def test_set_provider_model_filter(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = _make_ollama_provider(db)
    models = [
        DiscoveredModel(identifier="keep:1", display_name="Keep One", state="loaded"),
        DiscoveredModel(identifier="drop:2", display_name="Drop Two", state="loaded"),
    ]
    monkeypatch.setattr(
        "src.provider.service.get_discovery_client",
        lambda _t: type("_C", (), {"list_models": lambda self, base_url, api_key=None: models})(),
    )

    response = client.put(
        f"/api/providers/{provider.id}/models/filter",
        json={"allowed_models": ["keep:1", "keep:1", "  "]},
    )
    assert response.status_code == 200
    assert [m["identifier"] for m in response.json()["models"]] == ["keep:1"]

    # Filter persisted on the provider (deduped, blanks removed)
    provider_resp = client.get(f"/api/providers/{provider.id}")
    assert provider_resp.json()["allowed_models"] == ["keep:1"]


# ── persist (attach a discovered model to the canonical registry) ─────────────


def _local_family(db: Session) -> ModelFamily:
    """A keyless (LM Studio) family so persisted routes need no API key env."""
    family = ModelFamily(
        name="Local Family",
        family_identifier="test.local",
        provider_types=["lmstudio"],
    )
    db.add(family)
    db.commit()
    db.refresh(family)
    return family


def _local_provider(db: Session, name: str = "LM Studio") -> Provider:
    provider = Provider(name=name, provider_type=ProviderType.LMSTUDIO)
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


def test_persist_creates_new_registry(client: TestClient, db: Session) -> None:
    """Persisting an unknown identifier creates a canonical model with one route."""
    provider = _local_provider(db)
    family = _local_family(db)

    response = client.post(
        f"/api/providers/{provider.id}/models/persist",
        json={"model_identifier": "custom-model-v1"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "custom-model-v1"
    assert data["model_family_id"] == family.id
    assert len(data["routes"]) == 1
    assert data["routes"][0]["provider_id"] == provider.id
    assert data["routes"][0]["model_identifier"] == "custom-model-v1"
    assert data["active_route_id"] == data["routes"][0]["id"]


def test_persist_attaches_route_to_existing_registry_by_slug(
    client: TestClient, db: Session
) -> None:
    """A second provider serving the same slug is added as a route to the existing model."""
    family = _local_family(db)
    provider1 = _local_provider(db, name="LM Studio A")
    provider2 = _local_provider(db, name="LM Studio B")

    registry = ModelRegistry(
        slug="shared-model",
        display_name="Shared Model",
        original_identifier="shared-model",
        model_family_id=family.id,
    )
    db.add(registry)
    db.flush()
    route = ModelRoute(
        model_registry_id=registry.id,
        provider_id=provider1.id,
        model_identifier="shared-model",
    )
    db.add(route)
    db.flush()
    registry.active_route_id = route.id
    db.commit()
    db.refresh(registry)

    response = client.post(
        f"/api/providers/{provider2.id}/models/persist",
        json={"model_identifier": "shared-model"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == registry.id  # same canonical model, not a new one
    assert len(data["routes"]) == 2
    assert {r["provider_id"] for r in data["routes"]} == {provider1.id, provider2.id}


def test_persist_existing_route_is_idempotent(client: TestClient, db: Session) -> None:
    """Persisting an already-routed (provider, identifier) returns the owning model unchanged."""
    family = _local_family(db)
    provider = _local_provider(db)

    registry = ModelRegistry(
        slug="already-here",
        display_name="Already Here",
        original_identifier="already-here",
        model_family_id=family.id,
    )
    db.add(registry)
    db.flush()
    route = ModelRoute(
        model_registry_id=registry.id,
        provider_id=provider.id,
        model_identifier="already-here",
    )
    db.add(route)
    db.flush()
    registry.active_route_id = route.id
    db.commit()
    db.refresh(registry)

    response = client.post(
        f"/api/providers/{provider.id}/models/persist",
        json={"model_identifier": "already-here"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == registry.id
    assert len(data["routes"]) == 1
