"""HTTP tests for the data-bank CRUD router and the RAG search/status router.

Data-bank writes are driven through the ASGI ``client`` (its sync request session
commits them). ``RetrievalService`` is never instantiated for real: an autouse
fixture overrides the ``get_retrieval_service`` FastAPI dependency with a plain
mock whose async methods are ``AsyncMock`` for every test in this module.

This matters because the dev/CI ``.env`` enables RAG (``RAG__ENABLED=true``) and
points the embedder at a reachable server — without the override the create/
update/search endpoints would make live embedding calls and then issue a pgvector
``<=>`` query that SQLite cannot execute. The disabled → 409 branch is exercised
by overriding the factory to return ``None`` explicitly, so the test is
independent of the ambient ``RAG__ENABLED`` value.
"""

from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from src.core.config import settings
from src.main import app
from src.rag.dependencies import get_retrieval_service
from src.rag.retrieval_service import RetrievalService
from src.rag.schemas import RetrievedChunk


def _make_retrieval_mock() -> MagicMock:
    """A stand-in RetrievalService with all awaited methods stubbed as AsyncMock."""
    mock = MagicMock(spec=RetrievalService)
    mock.retrieve = AsyncMock(return_value=[])
    mock.vectorize_data_bank_entry = AsyncMock(return_value=None)
    mock.remove_embeddings = AsyncMock(return_value=None)
    return mock


@pytest.fixture(autouse=True)
def retrieval_mock() -> Iterator[MagicMock]:
    """Force every request in this module onto a stubbed RetrievalService.

    Overriding the whole factory means FastAPI never resolves its async-DB
    sub-dependencies, so the async SQLite connection is never opened and no
    embedding backend is contacted. Tests that assert on retrieval behaviour
    request this fixture by name to get the same mock instance.
    """
    mock = _make_retrieval_mock()
    app.dependency_overrides[get_retrieval_service] = lambda: mock
    try:
        yield mock
    finally:
        app.dependency_overrides.pop(get_retrieval_service, None)


def _create_entry(client: TestClient, name: str = "World Lore", **fields: Any) -> dict[str, Any]:
    """POST a data-bank entry through the client and return the created payload."""
    body = {"name": name, "content": "Some knowledge text.", **fields}
    response = client.post("/api/data-bank/", json=body)
    assert response.status_code == 201, response.text
    return response.json()


# =========================================================================== #
# Data Bank CRUD
# =========================================================================== #


# --- GET /api/data-bank/  (list_entries) ---


def test_list_entries_empty(client: TestClient) -> None:
    response = client.get("/api/data-bank/")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["meta"]["total"] == 0
    assert data["meta"]["has_more"] is False


def test_list_entries_returns_created(client: TestClient) -> None:
    _create_entry(client, name="Alpha")
    _create_entry(client, name="Beta")

    response = client.get("/api/data-bank/")
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["total"] == 2
    assert {item["name"] for item in data["items"]} == {"Alpha", "Beta"}


def test_list_entries_filter_by_scope(client: TestClient, sample_character: Any) -> None:
    _create_entry(client, name="Global Fact", scope="global")
    _create_entry(client, name="Char Fact", scope="character", character_id=sample_character.id)

    response = client.get("/api/data-bank/", params={"scope": "global"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Global Fact"


# --- POST /api/data-bank/  (create_entry) ---


def test_create_entry(client: TestClient) -> None:
    response = client.post(
        "/api/data-bank/",
        json={"name": "History", "content": "The kingdom fell in 1042.", "scope": "global"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "History"
    assert data["content"] == "The kingdom fell in 1042."
    assert data["scope"] == "global"
    assert data["character_id"] is None
    assert "id" in data


def test_create_entry_missing_name(client: TestClient) -> None:
    response = client.post("/api/data-bank/", json={"content": "no name"})
    assert response.status_code == 422


def test_create_entry_empty_content(client: TestClient) -> None:
    """``content`` has ``min_length=1``; an empty string fails validation."""
    response = client.post("/api/data-bank/", json={"name": "Named", "content": ""})
    assert response.status_code == 422


def test_create_entry_indexes_for_retrieval(client: TestClient, retrieval_mock: MagicMock) -> None:
    """With a live retrieval service the new entry is chunked/embedded for RAG."""
    response = client.post(
        "/api/data-bank/",
        json={"name": "Indexed", "content": "Embed me please."},
    )
    assert response.status_code == 201
    retrieval_mock.vectorize_data_bank_entry.assert_awaited_once()
    kwargs = retrieval_mock.vectorize_data_bank_entry.await_args.kwargs
    assert kwargs["entry_id"] == response.json()["id"]
    assert kwargs["content"] == "Embed me please."


def test_create_entry_survives_index_failure(client: TestClient, retrieval_mock: MagicMock) -> None:
    """A failed embed is swallowed — the entry is still created (best-effort index)."""
    retrieval_mock.vectorize_data_bank_entry.side_effect = RuntimeError("embed backend down")
    response = client.post(
        "/api/data-bank/",
        json={"name": "Resilient", "content": "Still saved."},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Resilient"


# --- GET /api/data-bank/{id}  (get_entry) ---


def test_get_entry(client: TestClient) -> None:
    created = _create_entry(client, name="Fetch Me")
    response = client.get(f"/api/data-bank/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Fetch Me"


def test_get_entry_not_found(client: TestClient) -> None:
    response = client.get("/api/data-bank/nonexistent-id")
    assert response.status_code == 404


# --- PUT /api/data-bank/{id}  (update_entry) ---


def test_update_entry(client: TestClient) -> None:
    created = _create_entry(client, name="Before", scope="global")
    response = client.put(
        f"/api/data-bank/{created['id']}",
        json={"name": "After", "content": "Revised text.", "scope": "character"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "After"
    assert data["content"] == "Revised text."
    assert data["scope"] == "character"


def test_update_entry_not_found(client: TestClient) -> None:
    response = client.put("/api/data-bank/nonexistent-id", json={"name": "X"})
    assert response.status_code == 404


def test_update_entry_empty_name(client: TestClient) -> None:
    created = _create_entry(client, name="Keep")
    response = client.put(f"/api/data-bank/{created['id']}", json={"name": ""})
    assert response.status_code == 422


def test_update_entry_reindexes(client: TestClient, retrieval_mock: MagicMock) -> None:
    created = _create_entry(client, name="Reindex Me")
    retrieval_mock.vectorize_data_bank_entry.reset_mock()

    response = client.put(
        f"/api/data-bank/{created['id']}",
        json={"content": "Fresh content to re-embed."},
    )
    assert response.status_code == 200
    retrieval_mock.vectorize_data_bank_entry.assert_awaited_once()


# --- DELETE /api/data-bank/{id}  (delete_entry) ---


def test_delete_entry(client: TestClient) -> None:
    created = _create_entry(client, name="ToDelete")
    response = client.delete(f"/api/data-bank/{created['id']}")
    assert response.status_code == 204
    assert client.get(f"/api/data-bank/{created['id']}").status_code == 404


def test_delete_entry_not_found(client: TestClient) -> None:
    response = client.delete("/api/data-bank/nonexistent-id")
    assert response.status_code == 404


def test_delete_entry_purges_embeddings(client: TestClient, retrieval_mock: MagicMock) -> None:
    created = _create_entry(client, name="Purge Me")
    response = client.delete(f"/api/data-bank/{created['id']}")
    assert response.status_code == 204
    retrieval_mock.remove_embeddings.assert_awaited_once_with("data_bank", created["id"])


# =========================================================================== #
# POST /api/rag/search
# =========================================================================== #


def test_search_returns_409_when_retrieval_disabled(client: TestClient) -> None:
    """When RAG is off, manual search reports a 409 conflict.

    Force the disabled branch by overriding the factory to ``None`` regardless of
    the ambient ``RAG__ENABLED`` (the client fixture clears overrides on teardown).
    """
    app.dependency_overrides[get_retrieval_service] = lambda: None
    response = client.post("/api/rag/search", json={"query": "anything"})
    assert response.status_code == 409


def test_search_returns_chunks(client: TestClient, retrieval_mock: MagicMock) -> None:
    chunks = [
        RetrievedChunk(
            content="The dragon guards the northern pass.",
            source_type="data_bank",
            source_id="db123456",
            score=0.91,
            chunk_index=0,
        ),
        RetrievedChunk(
            content="Second relevant chunk.",
            source_type="message",
            source_id="msg99",
            score=0.72,
            chunk_index=1,
        ),
    ]
    retrieval_mock.retrieve.return_value = chunks

    response = client.post("/api/rag/search", json={"query": "who guards the pass?"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    first = data[0]
    assert set(first) == {"content", "source_type", "source_id", "score", "chunk_index"}
    assert first["content"] == "The dragon guards the northern pass."
    assert first["source_type"] == "data_bank"
    assert first["score"] == 0.91
    retrieval_mock.retrieve.assert_awaited_once()


def test_search_passes_request_parameters(client: TestClient, retrieval_mock: MagicMock) -> None:
    """Request-body fields are forwarded to ``RetrievalService.retrieve`` verbatim."""
    response = client.post(
        "/api/rag/search",
        json={
            "query": "history",
            "chat_id": "chat123",
            "character_id": "char456",
            "max_results": 7,
            "threshold": 0.5,
        },
    )
    assert response.status_code == 200
    retrieval_mock.retrieve.assert_awaited_once_with(
        chat_id="chat123",
        query_text="history",
        character_id="char456",
        max_results=7,
        threshold=0.5,
    )


def test_search_defaults_blank_chat_id(client: TestClient, retrieval_mock: MagicMock) -> None:
    """A missing ``chat_id`` is forwarded to retrieval as an empty string, not None."""
    response = client.post("/api/rag/search", json={"query": "no chat"})
    assert response.status_code == 200
    assert retrieval_mock.retrieve.await_args.kwargs["chat_id"] == ""


def test_search_missing_query(client: TestClient, retrieval_mock: MagicMock) -> None:
    response = client.post("/api/rag/search", json={})
    assert response.status_code == 422
    retrieval_mock.retrieve.assert_not_awaited()


def test_search_empty_query(client: TestClient) -> None:
    """``query`` has ``min_length=1``; an empty string fails validation."""
    response = client.post("/api/rag/search", json={"query": ""})
    assert response.status_code == 422


def test_search_max_results_out_of_range(client: TestClient) -> None:
    """``max_results`` is capped at 50 (``le=50``)."""
    response = client.post("/api/rag/search", json={"query": "hi", "max_results": 100})
    assert response.status_code == 422


def test_search_threshold_out_of_range(client: TestClient) -> None:
    """``threshold`` must be within [0.0, 1.0] (``le=1.0``)."""
    response = client.post("/api/rag/search", json={"query": "hi", "threshold": 2.0})
    assert response.status_code == 422


# =========================================================================== #
# GET /api/rag/status
# =========================================================================== #


def test_rag_status_shape(client: TestClient) -> None:
    response = client.get("/api/rag/status")
    assert response.status_code == 200
    data = response.json()

    expected_keys = {
        "enabled",
        "provider",
        "model",
        "dimensions",
        "chunk_size",
        "chunk_overlap",
        "similarity_threshold",
        "max_results",
        "rerank",
    }
    assert set(data) == expected_keys
    assert set(data["rerank"]) == {"enabled", "model", "candidates", "score_threshold"}


def test_rag_status_mirrors_settings(client: TestClient) -> None:
    """The endpoint reports the live ``settings.rag`` configuration."""
    response = client.get("/api/rag/status")
    assert response.status_code == 200
    data = response.json()

    rag = settings.rag
    assert data["enabled"] == rag.enabled
    assert data["provider"] == rag.embedding.provider
    assert data["model"] == rag.embedding.model
    assert data["dimensions"] == rag.embedding.dimensions
    assert data["chunk_size"] == rag.chunk_size
    assert data["chunk_overlap"] == rag.chunk_overlap
    assert data["similarity_threshold"] == rag.similarity_threshold
    assert data["max_results"] == rag.max_results
    assert data["rerank"]["enabled"] == rag.rerank.enabled
    assert data["rerank"]["candidates"] == rag.rerank.candidates
