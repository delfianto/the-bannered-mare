"""Canonical types and abstract base for provider adapters."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TokenUsage:
    """Normalized token usage across all providers."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0


@dataclass
class CompletionResponse:
    """Normalized non-streaming completion response."""

    content: str
    finish_reason: str
    usage: TokenUsage
    reasoning: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamChunk:
    """Single chunk from a streaming completion response."""

    content: str | None = None
    reasoning: str | None = None
    finish_reason: str | None = None
    usage: TokenUsage | None = None


class ProviderAdapter(ABC):
    """
    Transforms requests/responses between canonical format and a provider's native API.

    Adapters are stateless data transformers — they do not make HTTP calls.
    The ProviderGateway owns the httpx client, timeouts, and error handling.
    """

    @abstractmethod
    def build_url(
        self,
        base_url: str,
        model: str,
        stream: bool,
        api_key: str | None = None,
    ) -> str:
        """Build the full request URL for this provider."""
        ...

    @abstractmethod
    def build_headers(self, api_key: str | None) -> dict[str, str]:
        """Build request headers (auth, content-type, version headers)."""
        ...

    @abstractmethod
    def build_payload(
        self,
        messages: list[dict[str, Any]],
        model: str,
        stream: bool,
        parameters: dict[str, Any],
        minimize_reasoning: bool = False,
    ) -> dict[str, Any]:
        """
        Convert canonical messages + parameters into the provider's request body.

        `messages` is in OpenAI format (list of {role, content} dicts).
        `parameters` is the merged dict from ModelFamily defaults + Model overrides.
        Each adapter selectively extracts the parameters it understands.

        `minimize_reasoning` requests that reasoning/thinking be turned off for this
        call (throwaway auxiliary generations). Each adapter translates that intent
        into its own transport's mechanism; the caller only sets it for families
        whose reasoning is actually controllable.
        """
        ...

    @abstractmethod
    def parse_response(self, data: dict[str, Any]) -> CompletionResponse:
        """Parse the provider's JSON response into a canonical CompletionResponse."""
        ...

    @abstractmethod
    def parse_stream_line(self, line: str) -> StreamChunk | None:
        """
        Parse a single SSE line into a StreamChunk.

        Returns None for lines that should be skipped (event: headers, pings,
        non-content payloads). Returns a StreamChunk with finish_reason set
        to signal end of stream.
        """
        ...

    def get_timeout(self, model: str) -> float:
        """Return the HTTP timeout in seconds for this model."""
        return 120.0
