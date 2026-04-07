"""Tests for provider router"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.provider import Provider, ProviderType


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
