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
        usage_data = data.get("usage", {})
        prompt_details = usage_data.get("prompt_tokens_details", {})

        # reasoning_content used by DeepSeek, xAI, OpenRouter reasoning models
        reasoning = message.get("reasoning_content") or message.get("reasoning") or None

        return CompletionResponse(
            content=message.get("content") or "",
            finish_reason=choice.get("finish_reason", "stop"),
            usage=TokenUsage(
                input_tokens=usage_data.get("prompt_tokens", 0),
                output_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
                cache_read_tokens=prompt_details.get("cached_tokens", 0),
            ),
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
        if not choices:
            return None

        choice = choices[0]
        delta = choice.get("delta", {})

        content = delta.get("content")
        reasoning = delta.get("reasoning_content") or delta.get("reasoning")
        finish_reason = choice.get("finish_reason")

        usage = None
        if "usage" in data and data["usage"]:
            u = data["usage"]
            pd = u.get("prompt_tokens_details", {})
            usage = TokenUsage(
                input_tokens=u.get("prompt_tokens", 0),
                output_tokens=u.get("completion_tokens", 0),
                total_tokens=u.get("total_tokens", 0),
                cache_read_tokens=pd.get("cached_tokens", 0),
            )

        if content is None and reasoning is None and finish_reason is None and usage is None:
            return None

        return StreamChunk(
            content=content,
            reasoning=reasoning,
            finish_reason=finish_reason,
            usage=usage,
        )
