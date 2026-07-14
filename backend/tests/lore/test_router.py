"""HTTP tests for the lorebook + lore-entry router.

Covers all eight endpoints (lorebook CRUD + entry CRUD) with a
request-validation, happy-path, and error-path case each. Every write is driven
through the ASGI ``client`` so the sync request session commits it — the shared
SQLite test DB then serves the follow-up read/get coherently.
"""

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.character import Character


def _create_lorebook(client: TestClient, name: str = "World Lore", **fields: Any) -> dict[str, Any]:
    """POST a lorebook through the client and return the created payload."""
    response = client.post("/api/lorebooks", json={"name": name, **fields})
    assert response.status_code == 201, response.text
    return response.json()


def _create_entry(
    client: TestClient,
    lorebook_id: str,
    name: str = "Dragon",
    content: str = "Dragons breathe fire.",
    **fields: Any,
) -> dict[str, Any]:
    """POST a lore entry through the client and return the created payload."""
    response = client.post(
        f"/api/lorebooks/{lorebook_id}/entries",
        json={"name": name, "content": content, **fields},
    )
    assert response.status_code == 201, response.text
    return response.json()


# --------------------------------------------------------------------------- #
# GET /api/lorebooks  (list_lorebooks)
# --------------------------------------------------------------------------- #


def test_list_lorebooks_empty(client: TestClient) -> None:
    response = client.get("/api/lorebooks")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["meta"]["total"] == 0
    assert data["meta"]["has_more"] is False


def test_list_lorebooks_returns_created(client: TestClient) -> None:
    _create_lorebook(client, name="First")
    _create_lorebook(client, name="Second")

    response = client.get("/api/lorebooks")
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["total"] == 2
    assert {item["name"] for item in data["items"]} == {"First", "Second"}


def test_list_lorebooks_filter_by_character(
    client: TestClient, sample_character: Character
) -> None:
    _create_lorebook(client, name="Char Book", character_id=sample_character.id)
    _create_lorebook(client, name="Global Book", is_global=True)

    response = client.get("/api/lorebooks", params={"character_id": sample_character.id})
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Char Book"
    assert items[0]["character_id"] == sample_character.id


def test_list_lorebooks_filter_by_global(client: TestClient) -> None:
    _create_lorebook(client, name="Global Book", is_global=True)
    _create_lorebook(client, name="Plain Book")

    response = client.get("/api/lorebooks", params={"is_global": "true"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Global Book"


def test_list_lorebooks_invalid_bool_query(client: TestClient) -> None:
    """A non-boolean ``is_global`` query value is rejected by FastAPI validation."""
    response = client.get("/api/lorebooks", params={"is_global": "not-a-bool"})
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# POST /api/lorebooks  (create_lorebook)
# --------------------------------------------------------------------------- #


def test_create_lorebook(client: TestClient) -> None:
    response = client.post(
        "/api/lorebooks",
        json={"name": "New Book", "description": "Notes", "is_global": True},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Book"
    assert data["description"] == "Notes"
    assert data["is_global"] is True
    assert data["character_id"] is None
    assert "id" in data


def test_create_lorebook_missing_name(client: TestClient) -> None:
    response = client.post("/api/lorebooks", json={"description": "no name"})
    assert response.status_code == 422


def test_create_lorebook_empty_name(client: TestClient) -> None:
    """``name`` has ``min_length=1``; an empty string fails validation."""
    response = client.post("/api/lorebooks", json={"name": ""})
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# GET /api/lorebooks/{id}  (get_lorebook)
# --------------------------------------------------------------------------- #


def test_get_lorebook_with_entries(client: TestClient) -> None:
    book = _create_lorebook(client, name="Detailed")
    _create_entry(client, book["id"], name="E1", content="Content one")
    _create_entry(client, book["id"], name="E2", content="Content two")

    response = client.get(f"/api/lorebooks/{book['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Detailed"
    assert len(data["entries"]) == 2
    assert {e["name"] for e in data["entries"]} == {"E1", "E2"}


def test_get_lorebook_not_found(client: TestClient) -> None:
    response = client.get("/api/lorebooks/nonexistent-id")
    assert response.status_code == 404


# --------------------------------------------------------------------------- #
# PUT /api/lorebooks/{id}  (update_lorebook)
# --------------------------------------------------------------------------- #


def test_update_lorebook(client: TestClient) -> None:
    book = _create_lorebook(client, name="Before")

    response = client.put(
        f"/api/lorebooks/{book['id']}",
        json={"name": "After", "description": "Updated"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "After"
    assert data["description"] == "Updated"


def test_update_lorebook_not_found(client: TestClient) -> None:
    response = client.put("/api/lorebooks/nonexistent-id", json={"name": "X"})
    assert response.status_code == 404


def test_update_lorebook_empty_name(client: TestClient) -> None:
    book = _create_lorebook(client, name="Keep")
    response = client.put(f"/api/lorebooks/{book['id']}", json={"name": ""})
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# DELETE /api/lorebooks/{id}  (delete_lorebook)
# --------------------------------------------------------------------------- #


def test_delete_lorebook(client: TestClient) -> None:
    book = _create_lorebook(client, name="ToDelete")

    response = client.delete(f"/api/lorebooks/{book['id']}")
    assert response.status_code == 204

    assert client.get(f"/api/lorebooks/{book['id']}").status_code == 404


def test_delete_lorebook_cascades_entries(client: TestClient, db: Session) -> None:
    """Deleting a lorebook removes its entries (delete-orphan cascade)."""
    from src.lore.models import LoreEntry

    book = _create_lorebook(client, name="Parent")
    _create_entry(client, book["id"], name="Child", content="Gone soon")

    response = client.delete(f"/api/lorebooks/{book['id']}")
    assert response.status_code == 204

    remaining = db.query(LoreEntry).filter(LoreEntry.lorebook_id == book["id"]).all()
    assert remaining == []


def test_delete_lorebook_not_found(client: TestClient) -> None:
    response = client.delete("/api/lorebooks/nonexistent-id")
    assert response.status_code == 404


# --------------------------------------------------------------------------- #
# POST /api/lorebooks/{id}/entries  (create_entry)
# --------------------------------------------------------------------------- #


def test_create_entry(client: TestClient) -> None:
    book = _create_lorebook(client, name="Entries Book")

    response = client.post(
        f"/api/lorebooks/{book['id']}/entries",
        json={
            "name": "Wyrm",
            "content": "Ancient fire-breathing serpent.",
            "keys": ["dragon", "wyrm"],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Wyrm"
    assert data["keys"] == ["dragon", "wyrm"]
    assert data["lorebook_id"] == book["id"]
    # Defaults from LoreEntryBase surface on the response.
    assert data["secondary_logic"] == "and_any"
    assert data["position"] == "after_character"
    assert data["enabled"] is True


def test_create_entry_lorebook_not_found(client: TestClient) -> None:
    response = client.post(
        "/api/lorebooks/nonexistent-id/entries",
        json={"name": "Orphan", "content": "No book"},
    )
    assert response.status_code == 404


def test_create_entry_missing_content(client: TestClient) -> None:
    book = _create_lorebook(client, name="Bad Entry Book")
    response = client.post(
        f"/api/lorebooks/{book['id']}/entries",
        json={"name": "No Content"},
    )
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# PUT /api/lorebooks/{id}/entries/{entry_id}  (update_entry)
# --------------------------------------------------------------------------- #


def test_update_entry(client: TestClient) -> None:
    book = _create_lorebook(client, name="Update Entry Book")
    entry = _create_entry(client, book["id"], name="Old", content="Old content")

    response = client.put(
        f"/api/lorebooks/{book['id']}/entries/{entry['id']}",
        json={"name": "New", "content": "New content", "priority": 250},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New"
    assert data["content"] == "New content"
    assert data["priority"] == 250


def test_update_entry_not_found(client: TestClient) -> None:
    book = _create_lorebook(client, name="Book Without Entry")
    response = client.put(
        f"/api/lorebooks/{book['id']}/entries/nonexistent-id",
        json={"name": "X"},
    )
    assert response.status_code == 404


def test_update_entry_invalid_depth(client: TestClient) -> None:
    """``depth`` has ``ge=0``; a negative value fails validation."""
    book = _create_lorebook(client, name="Depth Book")
    entry = _create_entry(client, book["id"])
    response = client.put(
        f"/api/lorebooks/{book['id']}/entries/{entry['id']}",
        json={"depth": -1},
    )
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# DELETE /api/lorebooks/{id}/entries/{entry_id}  (delete_entry)
# --------------------------------------------------------------------------- #


def test_delete_entry(client: TestClient) -> None:
    book = _create_lorebook(client, name="Delete Entry Book")
    entry = _create_entry(client, book["id"], name="ToGo")

    response = client.delete(f"/api/lorebooks/{book['id']}/entries/{entry['id']}")
    assert response.status_code == 204

    detail = client.get(f"/api/lorebooks/{book['id']}").json()
    assert detail["entries"] == []


def test_delete_entry_not_found(client: TestClient) -> None:
    book = _create_lorebook(client, name="Empty Book")
    response = client.delete(f"/api/lorebooks/{book['id']}/entries/nonexistent-id")
    assert response.status_code == 404
