"""OpenAI Chat Completions adapter — baseline for all OpenAI-compatible providers."""

import json
from typing import Any

from src.provider.adapters.base import (
    CompletionResponse,
    ProviderAdapter,
    StreamChunk,
    TokenUsage,
)

# Parameters accepted at the top level by OpenAI Chat Completions and the
# OpenAI-compatible surfaces we route through it (OpenRouter, xAI, LM Studio).
# Extra sampler knobs (top_k, min_p, top_a, repetition/repeat penalty) are not
# part of the OpenAI spec but are honored by OpenRouter and local runtimes; they
# only appear here for families whose schema defines them, so native OpenAI/xAI
# requests (which never carry them) are unaffected. The `thinking` object is
# handled separately (mapped to OpenRouter's `reasoning`), not passed raw.
_OPENAI_PARAMS = {
    "temperature",
    "top_p",
    "top_k",
    "min_p",
    "top_a",
    "n",
    "stop",
    "max_tokens",
    "max_completion_tokens",
    "presence_penalty",
    "frequency_penalty",
    "repetition_penalty",
    "repeat_penalty",
    "logit_bias",
    "logprobs",
    "top_logprobs",
    "response_format",
    "seed",
    "tools",
    "tool_choice",
    "parallel_tool_calls",
    "reasoning_effort",
    "verbosity",
    "agent_count",
    "user",
    "stream_options",
}


def _cache_tokens_from_normalized_usage(data: dict[str, Any]) -> tuple[int, int]:
    """Extract cache read/creation tokens from OpenCode Go's non-standard
    ``normalizedUsage`` top-level key.

    Zen's gateway injects ``normalizedUsage`` as a separate SSE chunk (sometimes
    tagged ``x-opencode-type: inference-cost``) before the standard ``usage``
    chunk. Fields: ``cacheReadTokens``, ``cacheWrite5mTokens``,
    ``cacheWrite1hTokens``. Returns ``(0, 0)`` when absent.
    """
    nu = data.get("normalizedUsage") or {}
    if not nu:
        return 0, 0
    cache_read = nu.get("cacheReadTokens", 0) or 0
    cache_creation = (nu.get("cacheWrite5mTokens", 0) or 0) + (nu.get("cacheWrite1hTokens", 0) or 0)
    return cache_read, cache_creation


def _token_usage_from(usage: dict[str, Any], data: dict[str, Any]) -> TokenUsage:
    """Build a TokenUsage from a standard OpenAI ``usage`` block.

    Shared by the blocking (``parse_response``) and streaming (``parse_stream_line``)
    paths. cache_read comes from ``prompt_tokens_details.cached_tokens``; when
    absent, fall back to OpenCode Go's non-standard ``normalizedUsage`` (carried on
    the same ``data`` payload) for both cache read and creation.
    """
    prompt_details = usage.get("prompt_tokens_details") or {}
    cache_read = prompt_details.get("cached_tokens", 0)
    cache_creation = 0
    if not cache_read:
        cache_read, cache_creation = _cache_tokens_from_normalized_usage(data)
    return TokenUsage(
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        total_tokens=usage.get("total_tokens", 0),
        cache_read_tokens=cache_read,
        cache_creation_tokens=cache_creation,
    )


class OpenAIAdapter(ProviderAdapter):
    """Adapter for OpenAI and OpenAI-compatible APIs (xAI, OpenRouter, vLLM, etc.)."""

    def build_url(
        self,
        base_url: str,
        model: str,
        stream: bool,
        api_key: str | None = None,
    ) -> str:
        return f"{base_url}/chat/completions"

    def build_headers(self, api_key: str | None) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def build_payload(
        self,
        messages: list[dict[str, Any]],
        model: str,
        stream: bool,
        parameters: dict[str, Any],
        minimize_reasoning: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": model, "messages": messages}

        if stream:
            payload["stream"] = True
            # Request usage in the final stream chunk so native-OpenAI streaming
            # returns token counts (OpenRouter and LM Studio accept it too).
            # A strict OpenAI-compat server that rejects it can be handled by
            # overriding build_payload in the adapter subclass to drop it.
            if "stream_options" not in payload:
                payload["stream_options"] = {"include_usage": True}

        for key, value in parameters.items():
            if key in _OPENAI_PARAMS:
                payload[key] = value

        # Map the native `thinking` toggle to OpenRouter's unified `reasoning`
        # object. Only open-weight families routed via OpenRouter carry `thinking`
        # (native OpenAI/xAI never do), so this stays OpenRouter-scoped in practice.
        # Skip when reasoning_effort is set — that already controls reasoning and
        # sending both risks a conflict.
        thinking = parameters.get("thinking")
        if (
            isinstance(thinking, dict)
            and thinking.get("type")
            and "reasoning_effort" not in parameters
        ):
            payload["reasoning"] = {"enabled": thinking["type"] != "disabled"}

        # Disable reasoning for throwaway auxiliary calls, via this transport's
        # mechanism (subclasses override _disable_reasoning).
        if minimize_reasoning:
            self._disable_reasoning(payload)

        return payload

    def _disable_reasoning(self, payload: dict[str, Any]) -> None:
        """Turn reasoning off for a throwaway call — OpenAI-native / local surface.

        The ``reasoning_effort`` "none" tier is the disable switch on native OpenAI
        (GPT-5.1+) and is honored by LM Studio; it is authoritative over any graded
        value or reasoning object set earlier. Aggregators with a different contract
        (OpenRouter) override this.
        """
        payload["reasoning_effort"] = "none"
        payload.pop("reasoning", None)

    def parse_response(self, data: dict[str, Any]) -> CompletionResponse:
        # Some providers return an empty choices list on a hard block/error (still
        # HTTP 200); guard the index and normalize to a filter terminal so the
        # completion classifier flags it rather than crashing.
        choices = data.get("choices")
        if not choices:
            u = data.get("usage") or {}
            return CompletionResponse(
                content="",
                finish_reason="content_filter",
                usage=TokenUsage(
                    input_tokens=u.get("prompt_tokens", 0),
                    output_tokens=u.get("completion_tokens", 0),
                    total_tokens=u.get("total_tokens", 0),
                ),
                raw=data,
            )
        choice = choices[0]
        message = choice.get("message", {})
        usage_data = data.get("usage") or {}

        # reasoning_content used by DeepSeek, xAI, OpenRouter reasoning models
        reasoning = message.get("reasoning_content") or message.get("reasoning") or None

        return CompletionResponse(
            content=message.get("content") or "",
            finish_reason=choice.get("finish_reason", "stop"),
            usage=_token_usage_from(usage_data, data),
            reasoning=reasoning,
            raw=data,
        )

    def parse_stream_line(self, line: str) -> StreamChunk | None:
        if not line.startswith("data: "):
            return None

        data_str = line[6:]
        if data_str == "[DONE]":
            return StreamChunk(finish_reason="stop")

        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            return None

        choices = data.get("choices", [])

        # Extract usage before the empty-choices guard — the final accounting
        # chunk (OpenAI stream_options.include_usage, OpenRouter accounting) has
        # choices: [] but carries the full usage block.
        usage = None
        if "usage" in data and data["usage"]:
            usage = _token_usage_from(data["usage"], data)
        elif "normalizedUsage" in data and data["normalizedUsage"]:
            # OpenCode Go sends normalizedUsage in a separate chunk (before the
            # standard usage chunk); parse cache tokens from it — the service
            # merges this with the standard usage via TokenUsage.merge().
            cr, cc = _cache_tokens_from_normalized_usage(data)
            usage = TokenUsage(cache_read_tokens=cr, cache_creation_tokens=cc)

        if not choices:
            if usage is not None:
                return StreamChunk(usage=usage)
            return None

        choice = choices[0]
        if not isinstance(choice, dict):
            return StreamChunk(usage=usage) if usage is not None else None
        delta = choice.get("delta") or {}
        finish_reason = choice.get("finish_reason")

        content = delta.get("content")
        reasoning = delta.get("reasoning_content") or delta.get("reasoning")

        if content is None and reasoning is None and finish_reason is None and usage is None:
            return None

        return StreamChunk(
            content=content,
            reasoning=reasoning,
            finish_reason=finish_reason,
            usage=usage,
        )
