"""Tests for ProviderGateway"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.provider.adapters import CompletionResponse
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
def mock_model() -> Any:
    model = MagicMock()
    model.model_identifier = "gpt-4"
    model.parameters = {"temperature": 0.7}
    model.model_family = MagicMock()
    model.model_family.parameters = {"max_tokens": {"type": "int", "default": 2000}}
    model.model_family.unsupported_parameters = []
    return model


def test_get_effective_parameters(mock_provider: Any, mock_model: Any) -> None:
    """Test parameter merging logic"""
    gateway = ProviderGateway(mock_provider, mock_model, mock_model.model_identifier)
    params = gateway._get_effective_parameters()  # pyright: ignore[reportPrivateUsage]

    assert params["max_tokens"] == 2000
    assert params["temperature"] == 0.7


@pytest.mark.asyncio
async def test_chat_completion_success(mock_provider: Any, mock_model: Any) -> None:
    """Test successful chat completion returns CompletionResponse"""
    gateway = ProviderGateway(mock_provider, mock_model, mock_model.model_identifier)
    messages = [{"role": "user", "content": "Hello"}]

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hi"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        result = await gateway.chat_completion(messages)

        assert isinstance(result, CompletionResponse)
        assert result.content == "Hi"
        assert result.finish_reason == "stop"
        assert result.usage.total_tokens == 7

        _ = mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer test_key"
