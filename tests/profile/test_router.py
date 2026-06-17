"""Tests for profile API endpoints"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.profile import Profile


def test_list_profiles_empty(client: TestClient) -> None:
    response = client.get("/api/profiles/")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["meta"]["total"] == 0


def test_create_profile(client: TestClient) -> None:
    response = client.post(
        "/api/profiles/",
        json={"name": "My Loadout", "description": "A test loadout"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My Loadout"
    assert data["source"] == "manual"
    assert data["is_default"] is False
    assert "id" in data


def test_create_profile_with_bad_ref_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/profiles/",
        json={"name": "Bad", "preset_id": "nonexistent"},
    )
    assert response.status_code == 404


def test_list_profiles(client: TestClient, db: Session) -> None:
    db.add_all([Profile(name="A"), Profile(name="B")])
    db.commit()

    response = client.get("/api/profiles/")
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["total"] == 2
    assert {item["name"] for item in data["items"]} == {"A", "B"}


def test_get_profile_not_found(client: TestClient) -> None:
    assert client.get("/api/profiles/nonexistent").status_code == 404


def test_update_profile(client: TestClient, db: Session) -> None:
    profile = Profile(name="Original")
    db.add(profile)
    db.commit()
    db.refresh(profile)

    response = client.put(f"/api/profiles/{profile.id}", json={"name": "Renamed"})
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


def test_delete_profile(client: TestClient, db: Session) -> None:
    profile = Profile(name="DeleteMe")
    db.add(profile)
    db.commit()
    db.refresh(profile)

    assert client.delete(f"/api/profiles/{profile.id}").status_code == 204
    assert db.query(Profile).filter(Profile.id == profile.id).first() is None


def test_set_default(client: TestClient, db: Session) -> None:
    p1 = Profile(name="First", is_default=True)
    p2 = Profile(name="Second", is_default=False)
    db.add_all([p1, p2])
    db.commit()
    db.refresh(p1)

    response = client.post(f"/api/profiles/{p2.id}/default")
    assert response.status_code == 200
    assert response.json()["is_default"] is True

    db.refresh(p1)
    assert p1.is_default is False
