"""Anthropic Messages API adapter."""

import json
from typing import Any

from src.provider.adapters.base import (
    CompletionResponse,
    ProviderAdapter,
    StreamChunk,
    TokenUsage,
)

_STOP_REASON_MAP: dict[str, str] = {
    "end_turn": "stop",
    "max_tokens": "length",
    "stop_sequence": "stop",
    "tool_use": "tool_calls",
}

_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicAdapter(ProviderAdapter):
    """Adapter for the Anthropic Messages API."""

    def build_url(
        self,
        base_url: str,
        model: str,
        stream: bool,
        api_key: str | None = None,
    ) -> str:
        return f"{base_url}/messages"

    def build_headers(self, api_key: str | None) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            headers["x-api-key"] = api_key
        headers["anthropic-version"] = _ANTHROPIC_VERSION
        # prompt-caching is GA but the header is still accepted; effort gates the
        # output_config.effort adaptive-thinking control on Opus 4.5+.
        headers["anthropic-beta"] = "prompt-caching-2024-07-31,effort-2025-11-24"
        return headers

    def build_payload(
        self,
        messages: list[dict[str, Any]],
        model: str,
        stream: bool,
        parameters: dict[str, Any],
        minimize_reasoning: bool = False,
    ) -> dict[str, Any]:
        system_parts: list[str] = []
        chat_messages: list[dict[str, Any]] = []

        for msg in messages:
            if msg.get("role") == "system":
                system_parts.append(msg.get("content", ""))
            else:
                chat_messages.append({"role": msg["role"], "content": msg.get("content", "")})

        payload: dict[str, Any] = {"model": model, "messages": chat_messages}

        if system_parts:
            system_text = "\n\n".join(system_parts)
            payload["system"] = [
                {
                    "type": "text",
                    "text": system_text,
                    "cache_control": {"type": "ephemeral"},
                }
            ]

        if stream:
            payload["stream"] = True

        # max_tokens is required by Anthropic
        payload["max_tokens"] = parameters.get("max_tokens", 4096)

        # temperature and top_p are mutually exclusive on Claude 4.x (sending both
        # 400s). Prefer temperature; only fall back to top_p when temperature is unset.
        temp = parameters.get("temperature")
        top_p = parameters.get("top_p")
        if temp is not None:
            payload["temperature"] = min(float(temp), 1.0)
        elif top_p is not None:
            payload["top_p"] = top_p

        top_k = parameters.get("top_k")
        if top_k is not None:
            payload["top_k"] = top_k

        stop_sequences = parameters.get("stop_sequences")
        if stop_sequences:
            payload["stop_sequences"] = stop_sequences

        thinking = parameters.get("thinking")
        # Forward any explicit thinking mode (enabled/disabled, and the adaptive
        # mode used by the newer tiers) — not just "enabled".
        if isinstance(thinking, dict) and thinking.get("type"):
            payload["thinking"] = thinking

        # Adaptive-thinking effort (Opus 4.5+/Sonnet 5/Fable) rides on
        # output_config.effort, gated by the effort beta header in build_headers.
        effort = parameters.get("effort")
        if effort is not None:
            payload["output_config"] = {"effort": effort}

        metadata = parameters.get("metadata")
        if isinstance(metadata, dict) and metadata:
            payload["metadata"] = metadata

        # Auxiliary calls disable thinking outright — authoritative over both the
        # forwarded thinking mode and the adaptive-effort output_config above.
        if minimize_reasoning:
            payload["thinking"] = {"type": "disabled"}
            payload.pop("output_config", None)

        return payload

    def parse_response(self, data: dict[str, Any]) -> CompletionResponse:
        content_blocks = data.get("content", [])
        text_parts = [
            block.get("text", "") for block in content_blocks if block.get("type") == "text"
        ]
        content = "".join(text_parts)

        # Extract thinking content from thinking blocks
        thinking_parts = [
            block.get("thinking", "") for block in content_blocks if block.get("type") == "thinking"
        ]
        reasoning = "".join(thinking_parts) or None

        raw_reason: str = data.get("stop_reason") or "end_turn"
        finish_reason = _STOP_REASON_MAP.get(raw_reason, raw_reason)

        usage_data = data.get("usage", {})

        return CompletionResponse(
            content=content,
            finish_reason=finish_reason,
            usage=TokenUsage(
                input_tokens=usage_data.get("input_tokens", 0),
                output_tokens=usage_data.get("output_tokens", 0),
                total_tokens=(
                    usage_data.get("input_tokens", 0) + usage_data.get("output_tokens", 0)
                ),
                cache_read_tokens=usage_data.get("cache_read_input_tokens", 0),
                cache_creation_tokens=usage_data.get("cache_creation_input_tokens", 0),
            ),
            reasoning=reasoning,
            raw=data,
        )

    def parse_stream_line(self, line: str) -> StreamChunk | None:
        if not line.startswith("data: "):
            return None

        data_str = line[6:]

        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            return None

        event_type = data.get("type")

        if event_type == "content_block_delta":
            delta = data.get("delta", {})
            delta_type = delta.get("type")
            if delta_type == "text_delta":
                return StreamChunk(content=delta.get("text"))
            if delta_type == "thinking_delta":
                return StreamChunk(reasoning=delta.get("thinking"))
            return None

        if event_type == "message_delta":
            delta = data.get("delta", {})
            raw_reason = delta.get("stop_reason", "end_turn")
            finish_reason = _STOP_REASON_MAP.get(raw_reason, raw_reason)
            usage_data = data.get("usage", {})
            usage = None
            if usage_data:
                usage = TokenUsage(output_tokens=usage_data.get("output_tokens", 0))
            return StreamChunk(finish_reason=finish_reason, usage=usage)

        if event_type == "message_stop":
            return StreamChunk(finish_reason="stop")

        return None

    def get_timeout(self, model: str) -> float:
        return 120.0
