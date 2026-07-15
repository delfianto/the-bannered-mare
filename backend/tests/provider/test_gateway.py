"""Tests for ProviderGateway — transport + wiring.

Pure parameter/reasoning resolution is covered in ``test_parameters.py`` and
status → exception mapping in ``test_http_errors.py``; this file focuses on the
gateway's own job: driving the adapter through httpx and surfacing failures.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from src.core.exceptions import ProviderAuthError, ProviderRateLimitError, ProviderTimeoutError
from src.provider.adapters import CompletionResponse, TokenUsage
from src.provider.gateway import ProviderGateway


@pytest.fixture
def mock_provider() -> Any:
    provider = MagicMock()
    provider.base_url = "https://api.openai.com/v1"
    provider.get_api_key.return_value = "test_key"
    provider.get_base_url.return_value = "https://api.openai.com/v1"
    provider.provider_type = MagicMock()
    provider.provider_type.value = "openai"
    return provider


@pytest.fixture
def mock_registry() -> Any:
    """A canonical model (registry): family + parameter overrides. The route's
    identifier is handed to the gateway separately, not read off the registry."""
    family = MagicMock()
    family.parameters = {
        "temperature": {"type": "float", "default": 1.0},
        "max_tokens": {"type": "int", "default": 2048},
    }
    family.unsupported_parameters = []
    registry = MagicMock()
    registry.parameters = {"temperature": 0.7}
    registry.model_family = family
    return registry


def test_gateway_exposes_passed_identity(mock_provider: Any, mock_registry: Any) -> None:
    """The gateway resolves through the identifier + registry it is handed."""
    gateway = ProviderGateway(mock_provider, mock_registry, "provider/gpt-4-turbo")

    assert gateway.active_identifier == "provider/gpt-4-turbo"
    assert gateway.provider is mock_provider
    assert gateway.registry is mock_registry


@pytest.mark.asyncio
async def test_chat_completion_success(mock_provider: Any, mock_registry: Any) -> None:
    """Successful chat completion returns parsed CompletionResponse."""
    gateway = ProviderGateway(mock_provider, mock_registry, "gpt-4")
    messages = [{"role": "user", "content": "Hello"}]

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hi"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await gateway.chat_completion(messages)

    assert isinstance(result, CompletionResponse)
    assert result.content == "Hi"
    assert result.finish_reason == "stop"
    assert result.usage.total_tokens == 7

    mock_client.post.assert_called_once()
    _, kwargs = mock_client.post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer test_key"


@pytest.mark.asyncio
async def test_chat_completion_adapter_parse_response_called(
    mock_provider: Any, mock_registry: Any
) -> None:
    """Verify that the adapter's parse_response is invoked with the response JSON."""
    gateway = ProviderGateway(mock_provider, mock_registry, "gpt-4")

    expected_response = CompletionResponse(
        content="parsed", finish_reason="stop", usage=TokenUsage()
    )

    raw_json = {"choices": [{"message": {"content": "parsed"}, "finish_reason": "stop"}]}
    mock_response = MagicMock()
    mock_response.json.return_value = raw_json
    mock_response.raise_for_status = MagicMock()

    with (
        patch("httpx.AsyncClient") as mock_client_cls,
        patch.object(
            gateway.adapter, "parse_response", return_value=expected_response
        ) as mock_parse,
    ):
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await gateway.chat_completion([{"role": "user", "content": "test"}])

    mock_parse.assert_called_once_with(raw_json)
    assert result.content == "parsed"


@pytest.mark.asyncio
async def test_chat_completion_auth_error(mock_provider: Any, mock_registry: Any) -> None:
    """HTTP 401 from the transport surfaces as ProviderAuthError."""
    gateway = ProviderGateway(mock_provider, mock_registry, "gpt-4")

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_response.reason_phrase = "Unauthorized"
    mock_response.json.return_value = {"error": {"message": "Invalid API key"}}

    http_error = httpx.HTTPStatusError("401", request=MagicMock(), response=mock_response)

    mock_post_response = MagicMock()
    mock_post_response.raise_for_status.side_effect = http_error

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_post_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with pytest.raises(ProviderAuthError, match="Invalid API key"):
            await gateway.chat_completion([{"role": "user", "content": "test"}])


@pytest.mark.asyncio
async def test_chat_completion_rate_limit(mock_provider: Any, mock_registry: Any) -> None:
    """HTTP 429 from the transport surfaces as ProviderRateLimitError."""
    gateway = ProviderGateway(mock_provider, mock_registry, "gpt-4")

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 429
    mock_response.reason_phrase = "Too Many Requests"
    mock_response.json.return_value = {"error": "Rate limit exceeded"}

    http_error = httpx.HTTPStatusError("429", request=MagicMock(), response=mock_response)

    mock_post_response = MagicMock()
    mock_post_response.raise_for_status.side_effect = http_error

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_post_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with pytest.raises(ProviderRateLimitError, match="Rate limit exceeded"):
            await gateway.chat_completion([{"role": "user", "content": "test"}])


@pytest.mark.asyncio
async def test_chat_completion_timeout(mock_provider: Any, mock_registry: Any) -> None:
    """httpx.TimeoutException maps to ProviderTimeoutError."""
    gateway = ProviderGateway(mock_provider, mock_registry, "gpt-4")

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("Connection timed out")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with pytest.raises(ProviderTimeoutError, match="Provider request timed out"):
            await gateway.chat_completion([{"role": "user", "content": "test"}])
