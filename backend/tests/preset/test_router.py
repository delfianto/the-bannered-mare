"""Tests for preset router"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.preset import Preset


def test_list_presets_empty(client: TestClient) -> None:
    """Test listing presets when none exist"""
    response = client.get("/api/presets/")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["meta"]["total"] == 0
    assert data["meta"]["has_more"] is False
    assert data["meta"]["page"] == 1
    assert data["meta"]["limit"] == 10


def test_list_presets(client: TestClient, db: Session) -> None:
    """Test listing presets with data"""
    p1 = Preset(name="Creative", parameters={"temperature": 1.2})
    p2 = Preset(name="Precise", parameters={"temperature": 0.3})
    db.add_all([p1, p2])
    db.commit()

    response = client.get("/api/presets/")
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["total"] == 2
    names = {item["name"] for item in data["items"]}
    assert "Creative" in names
    assert "Precise" in names


def test_create_preset(client: TestClient) -> None:
    """Test creating a preset"""
    response = client.post(
        "/api/presets/",
        json={
            "name": "My Preset",
            "description": "A test preset",
            "parameters": {"temperature": 0.7, "top_p": 0.9},
            "is_default": False,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My Preset"
    assert data["description"] == "A test preset"
    assert data["parameters"]["temperature"] == 0.7
    assert data["is_default"] is False
    assert "id" in data


def test_create_preset_as_default(client: TestClient) -> None:
    """Test creating a preset marked as default"""
    response = client.post(
        "/api/presets/",
        json={"name": "Default Preset", "parameters": {}, "is_default": True},
    )
    assert response.status_code == 201
    assert response.json()["is_default"] is True


def test_get_preset(client: TestClient, db: Session) -> None:
    """Test getting a preset by ID"""
    preset = Preset(name="GetMe", parameters={"temperature": 0.5})
    db.add(preset)
    db.commit()
    db.refresh(preset)

    response = client.get(f"/api/presets/{preset.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "GetMe"
    assert data["parameters"]["temperature"] == 0.5


def test_get_preset_not_found(client: TestClient) -> None:
    """Test getting a preset that does not exist"""
    response = client.get("/api/presets/nonexistent-id")
    assert response.status_code == 404


def test_update_preset(client: TestClient, db: Session) -> None:
    """Test updating a preset"""
    preset = Preset(name="Original", description="Old desc", parameters={"temperature": 1.0})
    db.add(preset)
    db.commit()
    db.refresh(preset)

    response = client.put(
        f"/api/presets/{preset.id}",
        json={
            "name": "Updated",
            "description": "New desc",
            "parameters": {"temperature": 0.5, "top_p": 0.8},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated"
    assert data["description"] == "New desc"
    assert data["parameters"]["temperature"] == 0.5
    assert data["parameters"]["top_p"] == 0.8


def test_update_preset_not_found(client: TestClient) -> None:
    """Test updating a preset that does not exist"""
    response = client.put(
        "/api/presets/nonexistent-id",
        json={"name": "Nope"},
    )
    assert response.status_code == 404


def test_delete_preset(client: TestClient, db: Session) -> None:
    """Test deleting a preset"""
    preset = Preset(name="DeleteMe", parameters={})
    db.add(preset)
    db.commit()
    db.refresh(preset)

    response = client.delete(f"/api/presets/{preset.id}")
    assert response.status_code == 204

    assert db.query(Preset).filter(Preset.id == preset.id).first() is None


def test_delete_preset_not_found(client: TestClient) -> None:
    """Test deleting a preset that does not exist"""
    response = client.delete("/api/presets/nonexistent-id")
    assert response.status_code == 404


def test_set_default(client: TestClient, db: Session) -> None:
    """Test setting a preset as default"""
    p1 = Preset(name="First", parameters={}, is_default=True)
    p2 = Preset(name="Second", parameters={}, is_default=False)
    db.add_all([p1, p2])
    db.commit()
    db.refresh(p1)
    db.refresh(p2)

    response = client.post(f"/api/presets/{p2.id}/default")
    assert response.status_code == 200
    data = response.json()
    assert data["is_default"] is True
    assert data["name"] == "Second"

    # Verify the old default was unset
    db.refresh(p1)
    assert p1.is_default is False


def test_set_default_not_found(client: TestClient) -> None:
    """Test setting default on a non-existent preset"""
    response = client.post("/api/presets/nonexistent-id/default")
    assert response.status_code == 404
