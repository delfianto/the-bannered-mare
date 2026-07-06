"""Tests for chat session router"""

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.core.persistence import Preset, Profile, PromptTemplate


def test_create_chat(
    client: TestClient, db: Session, sample_character: Any, sample_model: Any
) -> None:
    """Test creating a chat"""
    payload = {
        "character_id": sample_character.id,
        "model_id": sample_model.id,
        "title": "Test Chat",
    }
    response = client.post("/api/chats", json=payload)
    assert response.status_code == 201
    assert response.json()["title"] == "Test Chat"


def test_create_chat_no_model(client: TestClient, db: Session, sample_character: Any) -> None:
    """Test creating a chat without model"""
    payload = {
        "character_id": sample_character.id,
        # model_id omitted
        "title": "Chat No Model",
    }
    response = client.post("/api/chats", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Chat No Model"
    assert data["model"]["id"] is None


def test_list_chats(
    client: TestClient, db: Session, sample_character: Any, sample_model: Any
) -> None:
    """Test listing chats with character avatar info"""
    # Create a chat
    payload = {
        "character_id": sample_character.id,
        "model_id": sample_model.id,
        "title": "List Test Chat",
    }
    client.post("/api/chats", json=payload)

    # List chats
    response = client.get("/api/chats")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1

    chat = data["items"][0]
    assert chat["character"]["id"] == sample_character.id
    assert "avatar" in chat["character"]
    assert "avatar_thumbnail" in chat["character"]
    assert chat["character"]["avatar"] == sample_character.avatar
    assert chat["character"]["avatar_thumbnail"] == sample_character.avatar_thumbnail


def test_get_chat_details(
    client: TestClient, db: Session, sample_character: Any, sample_model: Any
) -> None:
    """Test getting chat details with character avatar info"""
    # Create a chat
    payload = {
        "character_id": sample_character.id,
        "model_id": sample_model.id,
        "title": "Detail Test Chat",
    }
    create_resp = client.post("/api/chats", json=payload)
    chat_id = create_resp.json()["id"]

    # Get chat details
    response = client.get(f"/api/chats/{chat_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == chat_id
    assert "avatar" in data["character"]
    assert "avatar_thumbnail" in data["character"]
    assert data["character"]["avatar"] == sample_character.avatar
    assert data["character"]["avatar_thumbnail"] == sample_character.avatar_thumbnail


def test_apply_profile_to_chat(
    client: TestClient, db: Session, sample_character: Any, sample_persona: Any
) -> None:
    """POST /api/chats/{id}/profile copies the profile's axes and records its name."""
    tmpl = PromptTemplate(name="RouterT", system_template="x")
    preset = Preset(name="RouterP", parameters={})
    db.add_all([tmpl, preset])
    db.commit()
    db.refresh(tmpl)
    db.refresh(preset)
    profile = Profile(
        name="Router Loadout",
        prompt_template_id=tmpl.id,
        preset_id=preset.id,
        persona_id=sample_persona.id,
    )
    db.add(profile)
    db.commit()

    chat_id = client.post(
        "/api/chats", json={"character_id": sample_character.id, "title": "Bare"}
    ).json()["id"]

    response = client.post(f"/api/chats/{chat_id}/profile", json={"profile_id": profile.id})
    assert response.status_code == 200
    data = response.json()
    assert data["template_id"] == tmpl.id
    assert data["preset_id"] == preset.id
    assert data["persona_id"] == sample_persona.id
    assert data["last_profile_name"] == "Router Loadout"
    assert data["initial_profile_name"] is None  # created bare


def test_apply_missing_profile_returns_404(
    client: TestClient, db: Session, sample_character: Any
) -> None:
    chat_id = client.post("/api/chats", json={"character_id": sample_character.id}).json()["id"]
    response = client.post(f"/api/chats/{chat_id}/profile", json={"profile_id": "nonexistent"})
    assert response.status_code == 404
