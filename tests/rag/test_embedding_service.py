"""Tests for EmbeddingService (mocked HTTP calls)"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from src.core.config import EmbeddingSettings
from src.rag.embedding_service import BATCH_SIZE, EmbeddingService


# These providers/models don't use EmbeddingGemma's prompt prefixes, so the helpers
# clear them to keep the asserted request payloads equal to the raw input.
def _ollama_settings(**overrides) -> EmbeddingSettings:
    defaults: dict[str, Any] = {
        "provider": "ollama",
        "model": "nomic-embed-text",
        "ollama_url": "http://localhost:11434",
        "query_prefix": "",
        "document_prefix": "",
    }
    defaults.update(overrides)
    return EmbeddingSettings(**defaults)


def _openai_settings(**overrides) -> EmbeddingSettings:
    defaults: dict[str, Any] = {
        "provider": "openai",
        "model": "text-embedding-3-small",
        "openai_url": "https://api.openai.com/v1",
        "openai_key_env": "OPENAI_API_KEY",
        "query_prefix": "",
        "document_prefix": "",
    }
    defaults.update(overrides)
    return EmbeddingSettings(**defaults)


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


@pytest.mark.asyncio
async def test_embed_ollama():
    settings = _ollama_settings()
    service = EmbeddingService(settings)

    embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    mock_resp = _mock_response({"embeddings": embeddings})

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.rag.embedding_service.httpx.AsyncClient", return_value=mock_client):
        result = await service.embed_documents(["hello", "world"])

    assert result == embeddings
    mock_client.post.assert_called_once_with(
        "http://localhost:11434/api/embed",
        json={"model": "nomic-embed-text", "input": ["hello", "world"]},
        timeout=60.0,
    )


@pytest.mark.asyncio
async def test_embed_openai(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    settings = _openai_settings()
    service = EmbeddingService(settings)

    api_response = {
        "data": [
            {"embedding": [0.1, 0.2, 0.3]},
            {"embedding": [0.4, 0.5, 0.6]},
        ]
    }
    mock_resp = _mock_response(api_response)

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.rag.embedding_service.httpx.AsyncClient", return_value=mock_client):
        result = await service.embed_documents(["hello", "world"])

    assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    mock_client.post.assert_called_once_with(
        "https://api.openai.com/v1/embeddings",
        json={"model": "text-embedding-3-small", "input": ["hello", "world"]},
        headers={"Authorization": "Bearer sk-test-key"},
        timeout=60.0,
    )


@pytest.mark.asyncio
async def test_embed_llamacpp_applies_embeddinggemma_prefixes():
    """llama.cpp hits /v1/embeddings (no auth) with EmbeddingGemma's query/doc prompts."""
    settings = EmbeddingSettings(
        provider="llamacpp",
        model="embeddinggemma",
        llamacpp_url="http://localhost:8080",
    )
    service = EmbeddingService(settings)

    mock_resp = _mock_response({"data": [{"embedding": [0.1, 0.2, 0.3]}]})
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.rag.embedding_service.httpx.AsyncClient", return_value=mock_client):
        doc_result = await service.embed_documents(["the dragon guards the keep"])
        query_result = await service.embed_query("who guards the keep?")

    assert doc_result == [[0.1, 0.2, 0.3]]
    assert query_result == [0.1, 0.2, 0.3]  # embed_query unwraps to a single vector

    doc_call, query_call = mock_client.post.call_args_list
    # OpenAI-compatible endpoint under /v1, and no Authorization header for local llama.cpp.
    assert doc_call.args[0] == "http://localhost:8080/v1/embeddings"
    assert doc_call.kwargs["headers"] == {}
    assert doc_call.kwargs["json"]["input"] == ["title: none | text: the dragon guards the keep"]
    assert query_call.kwargs["json"]["input"] == [
        "task: search result | query: who guards the keep?"
    ]


@pytest.mark.asyncio
async def test_embed_batching():
    settings = _ollama_settings()
    service = EmbeddingService(settings)

    texts = [f"text_{i}" for i in range(BATCH_SIZE + 3)]
    batch1_embeddings = [[float(i)] for i in range(BATCH_SIZE)]
    batch2_embeddings = [[float(i)] for i in range(BATCH_SIZE, BATCH_SIZE + 3)]

    call_count = 0

    async def mock_post(url, json, timeout):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            assert len(json["input"]) == BATCH_SIZE
            return _mock_response({"embeddings": batch1_embeddings})
        else:
            assert len(json["input"]) == 3
            return _mock_response({"embeddings": batch2_embeddings})

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = mock_post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.rag.embedding_service.httpx.AsyncClient", return_value=mock_client):
        result = await service.embed_documents(texts)

    assert call_count == 2
    assert len(result) == BATCH_SIZE + 3
    assert result == batch1_embeddings + batch2_embeddings


@pytest.mark.asyncio
async def test_embed_error_handling():
    settings = _ollama_settings()
    service = EmbeddingService(settings)

    mock_resp = _mock_response({}, status_code=500)

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("src.rag.embedding_service.httpx.AsyncClient", return_value=mock_client),
        pytest.raises(httpx.HTTPStatusError),
    ):
        await service.embed_documents(["fail"])
