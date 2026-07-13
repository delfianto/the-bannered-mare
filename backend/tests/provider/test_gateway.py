"""Tests for ProviderGateway"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from src.core.exceptions import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from src.core.persistence.enums import ReasoningMode
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
def mock_family() -> Any:
    family = MagicMock()
    family.parameters = {
        "temperature": {"type": "float", "default": 1.0, "min_value": 0.0, "max_value": 2.0},
        "max_tokens": {"type": "int", "default": 2048, "min_value": 1},
    }
    family.unsupported_parameters = []
    return family


@pytest.fixture
def mock_registry(mock_family: Any) -> Any:
    """A canonical model (registry): family + parameter overrides. The route's
    identifier is handed to the gateway separately, not read off the registry."""
    registry = MagicMock()
    registry.parameters = {"temperature": 0.7}
    registry.model_family = mock_family
    return registry


# --- constructor / identity ---


def test_gateway_uses_passed_identifier_and_registry_params(
    mock_provider: Any, mock_registry: Any
) -> None:
    """The gateway resolves through the identifier it is given and the registry's params."""
    gateway = ProviderGateway(mock_provider, mock_registry, "provider/gpt-4-turbo")

    assert gateway.active_identifier == "provider/gpt-4-turbo"
    assert gateway.provider is mock_provider
    assert gateway.registry is mock_registry
    # Registry override wins over the family default.
    params = gateway._get_effective_parameters()
    assert params["temperature"] == 0.7
    assert params["max_tokens"] == 2048


# --- _get_effective_parameters ---


def test_get_effective_parameters_family_defaults_only(mock_provider: Any) -> None:
    """Family defaults populate when the registry has no overrides."""
    family = MagicMock()
    family.parameters = {
        "temperature": {"type": "float", "default": 0.9},
        "max_tokens": {"type": "int", "default": 4096},
    }
    family.unsupported_parameters = []

    registry = MagicMock()
    registry.parameters = {}
    registry.model_family = family

    gateway = ProviderGateway(mock_provider, registry, "gpt-4")
    params = gateway._get_effective_parameters()

    assert params["temperature"] == 0.9
    assert params["max_tokens"] == 4096


def test_get_effective_parameters_model_overrides_family(
    mock_provider: Any, mock_registry: Any
) -> None:
    """Registry-level overrides take precedence over family defaults."""
    gateway = ProviderGateway(mock_provider, mock_registry, "gpt-4")
    params = gateway._get_effective_parameters()

    assert params["temperature"] == 0.7
    assert params["max_tokens"] == 2048


def test_get_effective_parameters_preset_overrides_all(
    mock_provider: Any, mock_registry: Any
) -> None:
    """Preset parameters override both family defaults and registry overrides."""
    preset_params = {"temperature": 0.3, "max_tokens": 512, "top_p": 0.95}
    gateway = ProviderGateway(
        mock_provider, mock_registry, "gpt-4", preset_parameters=preset_params
    )
    params = gateway._get_effective_parameters()

    assert params["temperature"] == 0.3
    assert params["max_tokens"] == 512
    assert params["top_p"] == 0.95


def test_get_effective_parameters_no_family(mock_provider: Any) -> None:
    """Handles a registry with no model_family gracefully."""
    registry = MagicMock()
    registry.parameters = {"temperature": 0.5}
    registry.model_family = None

    gateway = ProviderGateway(mock_provider, registry, "gpt-4")
    params = gateway._get_effective_parameters()

    assert params == {"temperature": 0.5}


def test_get_effective_parameters_skips_null_defaults(mock_provider: Any) -> None:
    """Family params with default=None are skipped."""
    family = MagicMock()
    family.parameters = {
        "temperature": {"type": "float", "default": None},
        "max_tokens": {"type": "int", "default": 1024},
    }
    family.unsupported_parameters = []

    registry = MagicMock()
    registry.parameters = {}
    registry.model_family = family

    gateway = ProviderGateway(mock_provider, registry, "gpt-4")
    params = gateway._get_effective_parameters()

    assert "temperature" not in params
    assert params["max_tokens"] == 1024


def test_get_effective_parameters_strips_unsupported(mock_provider: Any) -> None:
    """Params the family lists as unsupported are dropped from a registry/preset override."""
    family = MagicMock()
    family.parameters = {"max_tokens": {"type": "int", "default": 8192}}
    family.family_identifier = "openai/gpt-5-thinking"
    # A reasoning model rejects sampling knobs (400 if sent).
    family.unsupported_parameters = ["temperature", "top_p", "frequency_penalty"]

    registry = MagicMock()
    registry.display_name = "GPT-5.4"
    registry.parameters = {"temperature": 0.8}  # stale registry override
    registry.model_family = family

    # A loadout preset that (wrongly) sets rejected knobs.
    preset_params = {"top_p": 0.9, "frequency_penalty": 0.5, "max_tokens": 4096}
    gateway = ProviderGateway(mock_provider, registry, "gpt-5.4", preset_parameters=preset_params)
    params = gateway._get_effective_parameters()

    assert "temperature" not in params
    assert "top_p" not in params
    assert "frequency_penalty" not in params
    # Supported overrides survive.
    assert params["max_tokens"] == 4096


# --- _should_minimize_reasoning (capability gate) ---


def _registry_with_mode(mode: ReasoningMode) -> Any:
    family = MagicMock()
    family.reasoning_mode = mode
    registry = MagicMock()
    registry.model_family = family
    return registry


def test_should_minimize_reasoning_requires_the_flag(mock_provider: Any) -> None:
    """The gate is off unless the caller opts in, regardless of capability."""
    gateway = ProviderGateway(mock_provider, _registry_with_mode(ReasoningMode.OPTIONAL), "m")
    assert gateway._should_minimize_reasoning is False


def test_should_minimize_reasoning_only_when_controllable(mock_provider: Any) -> None:
    """With the flag set, only an OPTIONAL (controllable) family is minimized;
    NONE has nothing to disable and ALWAYS_ON can't be, so both are skipped."""
    for mode, expected in (
        (ReasoningMode.OPTIONAL, True),
        (ReasoningMode.NONE, False),
        (ReasoningMode.ALWAYS_ON, False),
    ):
        gateway = ProviderGateway(
            mock_provider, _registry_with_mode(mode), "m", minimize_reasoning=True
        )
        assert gateway._should_minimize_reasoning is expected


# --- chat_completion ---


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


# --- HTTP error mapping ---


@pytest.mark.asyncio
async def test_chat_completion_auth_error(mock_provider: Any, mock_registry: Any) -> None:
    """HTTP 401 maps to ProviderAuthError."""
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
    """HTTP 429 maps to ProviderRateLimitError."""
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


def test_get_effective_parameters_removes_negative_seed(mock_provider: Any) -> None:
    """A seed parameter with value < 0 (such as -1) is removed from effective parameters."""
    registry = MagicMock()
    registry.parameters = {}
    registry.model_family = None

    # Test with preset_parameters containing seed = -1
    gateway = ProviderGateway(
        mock_provider, registry, "gpt-4", preset_parameters={"seed": -1, "temperature": 0.7}
    )
    params = gateway._get_effective_parameters()
    assert "seed" not in params
    assert params["temperature"] == 0.7

    # Test with registry parameters containing seed = -2
    registry.parameters = {"seed": -2}
    gateway = ProviderGateway(mock_provider, registry, "gpt-4")
    params = gateway._get_effective_parameters()
    assert "seed" not in params

    # Test with non-negative seed (should be preserved)
    gateway = ProviderGateway(mock_provider, registry, "gpt-4", preset_parameters={"seed": 42})
    params = gateway._get_effective_parameters()
    assert params["seed"] == 42
