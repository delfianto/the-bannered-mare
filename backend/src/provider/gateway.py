"""Provider gateway — routes requests through the correct provider adapter."""

import logging
from collections.abc import AsyncIterator
from typing import Any, NoReturn, cast

import httpx

from src.core.exceptions import (
    ProviderAuthError,
    ProviderException,
    ProviderInvalidRequestError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from src.model.models import Model
from src.provider.adapters import CompletionResponse, StreamChunk, get_adapter
from src.provider.adapters.base import ProviderAdapter
from src.provider.models import Provider

logger = logging.getLogger(__name__)


class ProviderGateway:
    """Routes requests to AI providers through the correct adapter."""

    def __init__(
        self,
        provider: Provider,
        model: Model,
        routing_provider: Provider | None = None,
        preset_parameters: dict[str, Any] | None = None,
    ):
        self.model = model
        self.preset_parameters = preset_parameters

        # Route through the override provider when the model declares one; else
        # use its native provider. The adapter is chosen by the effective
        # provider's type — aggregators (OpenRouter/OpenCode) map to the OpenAI
        # adapter via the registry, so no format is special-cased here.
        if model.routing_provider_id:
            if routing_provider is None:
                raise ValueError("Routing provider is required for models with a routing override")
            effective = routing_provider
        else:
            effective = provider

        self.provider = effective
        self.active_identifier = model.active_identifier
        self.adapter: ProviderAdapter = get_adapter(effective.provider_type)

        self.base_url = (self.provider.get_base_url()).rstrip("/")
        self.api_key = self.provider.get_api_key()

    def _get_effective_parameters(self) -> dict[str, Any]:
        """Merge ModelFamily defaults → Model overrides → Preset overrides."""
        effective_params: dict[str, Any] = {}

        family = self.model.model_family
        if family:
            family_params = family.parameters or {}
            for param_key, cfg in family_params.items():
                if "default" in cfg and cfg["default"] is not None:
                    effective_params[param_key] = cfg["default"]

        if self.model.parameters:
            effective_params.update(cast(Any, self.model.parameters))

        if self.preset_parameters:
            effective_params.update(self.preset_parameters)

        # Drop parameters the family explicitly rejects before they reach the
        # provider. Family defaults never include these — only a model/preset
        # override can, so a stale loadout can't 400 the request (e.g. temperature
        # on a reasoning model, stop on Grok). The UI warns the user separately.
        if family and family.unsupported_parameters:
            unsupported = set(family.unsupported_parameters)
            dropped = [key for key in effective_params if key in unsupported]
            for key in dropped:
                del effective_params[key]
            if dropped:
                logger.info(
                    "Stripped unsupported parameters %s for model %s (family %s)",
                    dropped,
                    self.model.name,
                    family.family_identifier,
                )

        return effective_params

    def _handle_http_error(self, exc: httpx.HTTPStatusError) -> NoReturn:
        """Map HTTP status errors to custom Provider exceptions."""
        status_code = exc.response.status_code
        error_detail = None
        try:
            error_detail = exc.response.json()
        except Exception:
            error_detail = exc.response.text

        message = f"Provider API error: {exc.response.reason_phrase}"
        if isinstance(error_detail, dict) and "error" in error_detail:
            err = error_detail["error"]
            if isinstance(err, dict) and "message" in err:
                message = err["message"]
            elif isinstance(err, str):
                message = err

        if status_code == 401:
            raise ProviderAuthError(message, status_code, error_detail) from exc
        elif status_code == 429:
            raise ProviderRateLimitError(message, status_code, error_detail) from exc
        elif status_code == 400:
            raise ProviderInvalidRequestError(message, status_code, error_detail) from exc
        else:
            raise ProviderException(message, status_code, error_detail) from exc

    async def chat_completion(self, messages: list[dict[str, str]]) -> CompletionResponse:
        """
        Make a non-streaming chat completion request.

        Returns:
            CompletionResponse with typed content, finish_reason, and usage.
        """
        parameters = self._get_effective_parameters()
        url = self.adapter.build_url(self.base_url, self.active_identifier, False, self.api_key)
        headers = self.adapter.build_headers(self.api_key)
        payload = self.adapter.build_payload(messages, self.active_identifier, False, parameters)
        timeout = self.adapter.get_timeout(self.active_identifier)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                return self.adapter.parse_response(response.json())
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError("Provider request timed out", detail=str(e)) from e
        except Exception as e:
            if isinstance(e, ProviderException):
                raise
            raise ProviderException(f"Unexpected provider error: {e!s}", detail=str(e)) from e

    async def chat_completion_stream(
        self, messages: list[dict[str, str]]
    ) -> AsyncIterator[StreamChunk]:
        """
        Make a streaming chat completion request.

        Yields:
            StreamChunk objects. Chunks with finish_reason set signal stream end.
        """
        parameters = self._get_effective_parameters()
        url = self.adapter.build_url(self.base_url, self.active_identifier, True, self.api_key)
        headers = self.adapter.build_headers(self.api_key)
        payload = self.adapter.build_payload(messages, self.active_identifier, True, parameters)
        timeout = self.adapter.get_timeout(self.active_identifier)

        try:
            async with (
                httpx.AsyncClient(timeout=timeout) as client,
                client.stream("POST", url, headers=headers, json=payload) as response,
            ):
                if response.status_code != 200:
                    await response.aread()
                    response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    chunk = self.adapter.parse_stream_line(line)
                    if chunk is None:
                        continue

                    yield chunk

                    if chunk.finish_reason is not None:
                        return

        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError("Provider request timed out", detail=str(e)) from e
        except Exception as e:
            if isinstance(e, ProviderException):
                raise
            raise ProviderException(f"Unexpected provider error: {e!s}", detail=str(e)) from e
