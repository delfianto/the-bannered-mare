"""Tests for RerankService (mocked TEI /rerank calls)."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from src.core.config import RerankSettings
from src.rag.rerank_service import RerankService


def _mock_response(json_data: Any, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


def _client(mock_resp: MagicMock) -> AsyncMock:
    client = AsyncMock(spec=httpx.AsyncClient)
    client.post.return_value = mock_resp
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


@pytest.mark.asyncio
async def test_rerank_reorders_and_caps_top_n():
    """TEI returns [{index, score}, ...] best-first; we map to indices and cut to top_n."""
    service = RerankService(RerankSettings(huggingface_url="http://localhost:8091"))

    ranked = [{"index": 2, "score": 0.9}, {"index": 0, "score": 0.5}, {"index": 1, "score": 0.1}]
    mock_client = _client(_mock_response(ranked))

    with patch("src.rag.rerank_service.httpx.AsyncClient", return_value=mock_client):
        ranked = await service.rerank("who guards the keep?", ["a", "b", "c"], top_n=2)

    assert ranked == [(2, 0.9), (0, 0.5)]  # (index, score), best-first, capped at top_n
    mock_client.post.assert_called_once_with(
        "http://localhost:8091/rerank",
        json={"query": "who guards the keep?", "texts": ["a", "b", "c"]},
        timeout=60.0,
    )


@pytest.mark.asyncio
async def test_rerank_empty_texts_makes_no_call():
    service = RerankService(RerankSettings())
    with patch("src.rag.rerank_service.httpx.AsyncClient") as mock_cls:
        ranked = await service.rerank("q", [], top_n=5)
    assert ranked == []
    mock_cls.assert_not_called()


@pytest.mark.asyncio
async def test_rerank_propagates_http_error():
    """Errors surface to the caller; RetrievalService is what fails open to vector order."""
    service = RerankService(RerankSettings())
    mock_client = _client(_mock_response({}, status_code=500))

    with (
        patch("src.rag.rerank_service.httpx.AsyncClient", return_value=mock_client),
        pytest.raises(httpx.HTTPStatusError),
    ):
        await service.rerank("q", ["a", "b"], top_n=5)
