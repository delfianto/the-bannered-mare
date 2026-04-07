"""Tests for model family router"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.model_family import ModelFamily


def test_list_model_families(client: TestClient, db: Session) -> None:
    """Test listing model families"""
    family = ModelFamily(
        name="GPT", family_identifier="test.gpt", parameters={"temperature": {"supported": True}}
    )
    db.add(family)
    db.commit()

    response = client.get("/api/model-families")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "meta" in data
    assert any(f["name"] == "GPT" for f in data["items"])
    # Verify heavy fields are excluded from list view
    for item in data["items"]:
        assert "parameters" not in item


def test_list_model_families_with_filter(client: TestClient, db: Session) -> None:
    """Test listing model families with name filter"""
    family1 = ModelFamily(
        name="GPT-4",
        family_identifier="gpt.4",
        parameters={"temperature": {"supported": True}},
        provider_types=["openai"],
    )
    family2 = ModelFamily(
        name="Claude",
        family_identifier="claude.3",
        parameters={"temperature": {"supported": True}},
        provider_types=["anthropic"],
    )
    db.add(family1)
    db.add(family2)
    db.commit()

    # Search for GPT
    response = client.get("/api/model-families?name__ilike=gpt")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "GPT-4"

    # Search for Claude
    response = client.get("/api/model-families?name__ilike=CLAude")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "Claude"

    # Search for something non-existent
    response = client.get("/api/model-families?name__ilike=NonExistent")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 0


def test_get_parameter_docs(client: TestClient) -> None:
    """Test parameter docs endpoint"""
    response = client.get("/api/model-families/parameter-docs")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
