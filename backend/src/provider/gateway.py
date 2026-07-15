"""Provider gateway — routes requests through the correct provider adapter.

This class owns only the httpx transport (open client → adapter builds the
request → send → adapter parses the response). The pure request-shaping lives in
``parameters.py`` (parameter merge + reasoning gate) and ``http_errors.py``
(status → domain-exception mapping), so each is testable on its own.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx

from src.core.exceptions import ProviderException, ProviderTimeoutError
from src.model.models import ModelRegistry
from src.provider.adapters import CompletionResponse, StreamChunk, get_adapter
from src.provider.adapters.base import ProviderAdapter
from src.provider.http_errors import map_http_error
from src.provider.models import Provider
from src.provider.parameters import resolve_effective_parameters, should_minimize_reasoning


class ProviderGateway:
    """Routes requests to AI providers through the correct adapter.

    Callers resolve a canonical model's active route and hand the gateway the
    route's ``provider`` + ``model_identifier`` plus the ``registry`` (for the
    family + parameter values). The provider *is* the route.
    """

    def __init__(
        self,
        provider: Provider,
        registry: ModelRegistry,
        model_identifier: str,
        preset_parameters: dict[str, Any] | None = None,
        minimize_reasoning: bool = False,
        client: httpx.AsyncClient | None = None,
    ):
        self.registry = registry
        self.preset_parameters = preset_parameters
        # Auxiliary calls (titles, tone chips, reply suggestions) set this to
        # suppress reasoning tokens on thinking-capable task models.
        self.minimize_reasoning = minimize_reasoning
        # The adapter is chosen by the provider's type — aggregators
        # (OpenRouter/OpenCode) map to the OpenAI adapter via the registry, so no
        # format is special-cased here.
        self.provider = provider
        self.active_identifier = model_identifier
        self.adapter: ProviderAdapter = get_adapter(provider.provider_type)
        self.base_url = (self.provider.get_base_url()).rstrip("/")
        self.api_key = self.provider.get_api_key()
        # An injected client (tests) is caller-owned and reused; production leaves
        # this None so each call opens and closes its own.
        self._client = client

    def effective_parameters(self) -> dict[str, Any]:
        """Merged/stripped sampler params (family → model → preset)."""
        return resolve_effective_parameters(self.registry, self.preset_parameters)

    # Pre-extraction method names kept as thin delegators for callers/tests that
    # still reach for them; the logic now lives in ``parameters.py``.
    def _get_effective_parameters(self) -> dict[str, Any]:
        return resolve_effective_parameters(self.registry, self.preset_parameters)

    @property
    def _should_minimize_reasoning(self) -> bool:
        return should_minimize_reasoning(self.registry, self.minimize_reasoning)

    @asynccontextmanager
    async def _http_client(self, timeout: float) -> AsyncIterator[httpx.AsyncClient]:
        """Yield the injected (caller-owned) client, or a fresh per-call one."""
        if self._client is not None:
            yield self._client
        else:
            async with httpx.AsyncClient(timeout=timeout) as client:
                yield client

    async def chat_completion(self, messages: list[dict[str, str]]) -> CompletionResponse:
        """Make a non-streaming chat completion request.

        Returns:
            CompletionResponse with typed content, finish_reason, and usage.
        """
        parameters = self.effective_parameters()
        url = self.adapter.build_url(self.base_url, self.active_identifier, False, self.api_key)
        headers = self.adapter.build_headers(self.api_key)
        payload = self.adapter.build_payload(
            messages, self.active_identifier, False, parameters, self._should_minimize_reasoning
        )
        timeout = self.adapter.get_timeout(self.active_identifier)

        try:
            async with self._http_client(timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                return self.adapter.parse_response(response.json())
        except httpx.HTTPStatusError as e:
            map_http_error(e)
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError("Provider request timed out", detail=str(e)) from e
        except Exception as e:
            if isinstance(e, ProviderException):
                raise
            raise ProviderException(f"Unexpected provider error: {e!s}", detail=str(e)) from e

    async def chat_completion_stream(
        self, messages: list[dict[str, str]]
    ) -> AsyncIterator[StreamChunk]:
        """Make a streaming chat completion request.

        Yields:
            StreamChunk objects. Chunks with finish_reason set signal stream end.
        """
        parameters = self.effective_parameters()
        url = self.adapter.build_url(self.base_url, self.active_identifier, True, self.api_key)
        headers = self.adapter.build_headers(self.api_key)
        payload = self.adapter.build_payload(
            messages, self.active_identifier, True, parameters, self._should_minimize_reasoning
        )
        timeout = self.adapter.get_timeout(self.active_identifier)

        try:
            async with (
                self._http_client(timeout) as client,
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
            map_http_error(e)
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError("Provider request timed out", detail=str(e)) from e
        except Exception as e:
            if isinstance(e, ProviderException):
                raise
            raise ProviderException(f"Unexpected provider error: {e!s}", detail=str(e)) from e
