"""Tests for provider router"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
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


def test_list_available_models_unsupported_provider_type(client: TestClient, db: Session) -> None:
    """Cloud providers don't support model auto-detection"""
    provider = Provider(name="OpenAI", provider_type=ProviderType.OPENAI)
    db.add(provider)
    db.commit()
    db.refresh(provider)

    response = client.get(f"/api/providers/{provider.id}/models/available")
    assert response.status_code == 400


def test_list_available_models(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = _make_ollama_provider(db)
    models = [DiscoveredModel(identifier="llama3:8b", display_name="llama3:8b", state="loaded")]
    monkeypatch.setattr(
        "src.provider.service.get_discovery_client",
        lambda _t: type("_C", (), {"list_models": lambda self, base_url: models})(),
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
        lambda _t: type("_C", (), {"list_models": lambda self, base_url: []})(),
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
