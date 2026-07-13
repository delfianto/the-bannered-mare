"""OpenRouter adapter — OpenAI-compatible aggregator with a unified reasoning API."""

from typing import Any

from src.provider.adapters.openai import OpenAIAdapter

_CACHE_CONTROL: dict[str, str] = {"type": "ephemeral"}


def _to_cached_block(text: str) -> list[dict[str, Any]]:
    """Wrap a string into an OpenAI-style content array with a cache_control breakpoint."""
    return [{"type": "text", "text": text, "cache_control": _CACHE_CONTROL}]


class OpenRouterAdapter(OpenAIAdapter):
    """Adapter for OpenRouter's OpenAI-compatible ``/chat/completions`` endpoint.

    OpenRouter exposes a single ``reasoning`` object that it normalizes to each
    underlying model's native control (``enable_thinking``, ``thinking={disabled}``,
    ``reasoning_effort``, …). Disabling therefore uses ``reasoning.enabled=false``
    rather than the OpenAI-native ``reasoning_effort`` "none" tier — the flat effort
    param has no portable "off" value across OpenRouter's open-weight models (e.g.
    Kimi only accepts low/medium/high), whereas ``reasoning.enabled=false`` disables
    uniformly. Everything else (URL, auth, sampler params) is inherited unchanged.

    For Anthropic-family models (``anthropic/*`` ids), OpenRouter forwards
    ``cache_control`` on text parts inside OpenAI-style content arrays to
    Anthropic's native prompt-caching API. Two breakpoints are added: one on the
    first system message (the stable scaffolding) and one on the last message
    (history tail) — matching the native Anthropic adapter's layout. Savings are
    reported back via ``usage.prompt_tokens_details.cached_tokens``, already
    parsed by the OpenAI adapter. Non-Anthropic models are left untouched
    (DeepSeek/GLM/Kimi auto-cache without explicit breakpoints).
    """

    def _disable_reasoning(self, payload: dict[str, Any]) -> None:
        payload["reasoning"] = {"enabled": False}
        payload.pop("reasoning_effort", None)

    def build_payload(
        self,
        messages: list[dict[str, Any]],
        model: str,
        stream: bool,
        parameters: dict[str, Any],
        minimize_reasoning: bool = False,
    ) -> dict[str, Any]:
        payload = super().build_payload(messages, model, stream, parameters, minimize_reasoning)

        if not model.startswith("anthropic/"):
            return payload

        msgs = payload["messages"]
        if not msgs:
            return payload

        # First system message → cached scaffolding breakpoint.
        for msg in msgs:
            if msg.get("role") == "system" and isinstance(msg.get("content"), str):
                msg["content"] = _to_cached_block(msg["content"])
                break

        # Last message → history-tail breakpoint. Skip if it's the same as the
        # system message we just marked (single-message edge case).
        last = msgs[-1]
        if isinstance(last.get("content"), str):
            last["content"] = _to_cached_block(last["content"])

        return payload
