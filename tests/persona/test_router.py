"""Tests for persona router"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.persona import Persona


def test_list_personas_empty(client: TestClient) -> None:
    """Test listing personas when none exist"""
    response = client.get("/api/personas/")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["meta"]["total"] == 0
    assert data["meta"]["has_more"] is False
    assert data["meta"]["page"] == 1
    assert data["meta"]["limit"] == 10


def test_create_persona(client: TestClient) -> None:
    """Test creating a persona"""
    response = client.post(
        "/api/personas/", data={"name": "Test Persona", "description": "Description"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Persona"
    assert "id" in data


def test_get_persona(client: TestClient, db: Session) -> None:
    """Test getting a persona by ID"""
    persona = Persona(name="GetMe", description="Desc")
    db.add(persona)
    db.commit()
    db.refresh(persona)

    response = client.get(f"/api/personas/{persona.id}")
    assert response.status_code == 200
    assert response.json()["name"] == "GetMe"


def test_create_persona_with_description(client: TestClient) -> None:
    """Test creating a persona with all basic fields"""
    response = client.post(
        "/api/personas/",
        data={"name": "Full Persona", "description": "A detailed persona", "is_default": "false"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Full Persona"
    assert data["description"] == "A detailed persona"
    assert data["is_default"] is False


def test_update_persona(client: TestClient, db: Session) -> None:
    """Test updating a persona"""
    persona = Persona(name="Original", description="Old desc")
    db.add(persona)
    db.commit()
    db.refresh(persona)

    response = client.put(
        f"/api/personas/{persona.id}",
        data={"name": "Updated", "description": "New desc"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated"
    assert data["description"] == "New desc"


def test_update_persona_not_found(client: TestClient) -> None:
    """Test updating a persona that does not exist"""
    response = client.put(
        "/api/personas/nonexistent-id",
        data={"name": "Nope"},
    )
    assert response.status_code == 404


def test_delete_persona(client: TestClient, db: Session) -> None:
    """Test deleting a persona"""
    persona = Persona(name="DeleteMe")
    db.add(persona)
    db.commit()
    db.refresh(persona)

    response = client.delete(f"/api/personas/{persona.id}")
    assert response.status_code == 204

    # Verify deleted
    assert db.query(Persona).filter(Persona.id == persona.id).first() is None


def test_delete_persona_not_found(client: TestClient) -> None:
    """Test deleting a persona that does not exist"""
    response = client.delete("/api/personas/nonexistent-id")
    assert response.status_code == 404


def test_set_default_persona(client: TestClient, db: Session) -> None:
    """Test setting a persona as default"""
    p1 = Persona(name="First", is_default=True)
    p2 = Persona(name="Second", is_default=False)
    db.add_all([p1, p2])
    db.commit()
    db.refresh(p1)
    db.refresh(p2)

    response = client.post(f"/api/personas/{p2.id}/set-default")
    assert response.status_code == 200
    data = response.json()
    assert data["is_default"] is True
    assert data["name"] == "Second"

    db.refresh(p1)
    assert p1.is_default is False
