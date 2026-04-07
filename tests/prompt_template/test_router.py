"""Tests for prompt template router"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.prompt_template import PromptTemplate


def test_list_templates(client: TestClient, db: Session) -> None:
    """Test listing prompt templates"""
    template = PromptTemplate(name="Test", system_template="Hello {{char}}")
    db.add(template)
    db.commit()

    response = client.get("/api/prompt-templates/")
    assert response.status_code == 200
    data = response.json()
    assert any(t["name"] == "Test" for t in data["items"])


def test_create_template(client: TestClient) -> None:
    """Test creating a prompt template"""
    payload = {"name": "New Template", "system_template": "Hello {{char}}", "description": "Desc"}
    response = client.post("/api/prompt-templates/", json=payload)
    assert response.status_code == 201
    assert response.json()["name"] == "New Template"
