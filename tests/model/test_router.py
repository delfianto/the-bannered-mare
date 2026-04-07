"""API tests for Models"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.core.persistence import get_db
from src.main import app
from src.model import Model
from src.model_family import ModelFamily
from src.provider import Provider, ProviderType


@pytest.fixture
def client(db_session: Session):  # type: ignore[no-untyped-def]
    """Create a TestClient with overridden database dependency"""

    def override_get_db():  # type: ignore[no-untyped-def]
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_list_models_does_not_embed_family(client: TestClient, db_session: Session) -> None:
    """Test that listing models returns basic info without embedded family"""
    # Setup
    provider = Provider(name="OpenAI", provider_type=ProviderType.OPENAI)
    db_session.add(provider)
    family = ModelFamily(
        name="GPT", family_identifier="test.gpt", parameters={"temperature": {"supported": True}}
    )
    db_session.add(family)
    db_session.commit()

    model = Model(
        name="GPT-4",
        provider_id=provider.id,
        model_identifier="gpt-4",
        model_family_id=family.id,
    )
    db_session.add(model)
    db_session.commit()

    # Act
    response = client.get("/api/models")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["id"] == model.id
    assert item["model_family_id"] == family.id
    # Ensure embedded object and heavy fields are NOT present in list view
    assert "model_family" not in item
    assert "parameters" not in item
    assert "template_id" not in item


def test_get_model_embeds_family(client: TestClient, db_session: Session) -> None:
    """Test that getting a model by ID returns detailed info with embedded family"""
    # Setup
    provider = Provider(name="Anthropic", provider_type=ProviderType.ANTHROPIC)
    db_session.add(provider)
    family = ModelFamily(
        name="Claude",
        family_identifier="test.claude",
        parameters={"temperature": {"supported": True}},
    )
    db_session.add(family)
    db_session.commit()

    model = Model(
        name="Claude 3",
        provider_id=provider.id,
        model_identifier="claude-3-opus",
        model_family_id=family.id,
    )
    db_session.add(model)
    db_session.commit()

    # Act
    response = client.get(f"/api/models/{model.id}")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == model.id
    assert data["model_family_id"] == family.id

    # Ensure embedded object and full fields ARE present in detail view
    assert "model_family" in data
    assert data["model_family"]["id"] == family.id
    assert data["model_family"]["name"] == "Claude"
    assert "parameters" in data
    assert "template_id" in data


def test_list_models_with_filter(client: TestClient, db_session: Session) -> None:
    """Test listing models with name filter"""
    provider = Provider(name="OpenAI", provider_type=ProviderType.OPENAI)
    db_session.add(provider)
    family = ModelFamily(
        name="GPT", family_identifier="test.gpt", parameters={"temperature": {"supported": True}}
    )
    db_session.add(family)
    db_session.commit()

    model1 = Model(
        name="GPT-4",
        provider_id=provider.id,
        model_identifier="gpt-4",
        model_family_id=family.id,
    )
    model2 = Model(
        name="GPT-3.5",
        provider_id=provider.id,
        model_identifier="gpt-3.5-turbo",
        model_family_id=family.id,
    )
    model3 = Model(
        name="Claude",
        provider_id=provider.id,
        model_identifier="claude",
        model_family_id=family.id,
    )
    db_session.add_all([model1, model2, model3])
    db_session.commit()

    # Search for GPT
    response = client.get("/api/models?name__ilike=gpt")
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["total"] == 2
    assert len(data["items"]) == 2
    names = [m["name"] for m in data["items"]]
    assert "GPT-4" in names
    assert "GPT-3.5" in names

    # Search for Claude
    response = client.get("/api/models?name__ilike=claude")
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["total"] == 1
    assert data["items"][0]["name"] == "Claude"
