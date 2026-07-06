"""Tests for character router"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.character import Character


def test_list_characters_empty(client: TestClient) -> None:
    """Test listing characters when none exist"""
    response = client.get("/api/characters")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["meta"]["total"] == 0
    assert data["meta"]["has_more"] is False
    assert data["meta"]["page"] == 1
    assert data["meta"]["limit"] == 10


def test_create_character(client: TestClient) -> None:
    """Test creating a character"""
    response = client.post(
        "/api/characters", data={"name": "Test Character", "description": "Description"}
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Test Character"


def test_create_character_with_gender(client: TestClient) -> None:
    """Test creating a character with gender fields"""
    response = client.post(
        "/api/characters",
        data={
            "name": "Gender Test",
            "gender": "others",
            "custom_gender": "Xenomorph",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Gender Test"
    assert data["gender"] == "others"
    assert data["custom_gender"] == "Xenomorph"


def test_create_character_minimal(client: TestClient) -> None:
    """Test creating a character with just a name (minimal fields)"""
    response = client.post("/api/characters", data={"name": "Minimal Char"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Minimal Char"
    assert data["description"] is None
    assert data["personality"] is None
    assert data["first_message"] is None
    assert "id" in data


def test_get_character(client: TestClient, db: Session) -> None:
    """Test getting a character by ID"""
    character = Character(name="GetMe")
    db.add(character)
    db.commit()
    db.refresh(character)

    response = client.get(f"/api/characters/{character.id}")
    assert response.status_code == 200
    assert response.json()["name"] == "GetMe"


def test_delete_character(client: TestClient, db: Session) -> None:
    """Test deleting a character"""
    character = Character(name="DeleteMe")
    db.add(character)
    db.commit()
    db.refresh(character)

    response = client.delete(f"/api/characters/{character.id}")
    assert response.status_code == 204

    assert db.query(Character).filter(Character.id == character.id).first() is None


def test_delete_character_not_found(client: TestClient) -> None:
    """Test deleting a non-existent character"""
    response = client.delete("/api/characters/nonexistent-id")
    assert response.status_code == 404
