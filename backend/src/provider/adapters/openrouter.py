"""OpenRouter adapter — OpenAI-compatible aggregator with a unified reasoning API."""

from typing import Any

from src.provider.adapters.openai import OpenAIAdapter


class OpenRouterAdapter(OpenAIAdapter):
    """Adapter for OpenRouter's OpenAI-compatible ``/chat/completions`` endpoint.

    OpenRouter exposes a single ``reasoning`` object that it normalizes to each
    underlying model's native control (``enable_thinking``, ``thinking={disabled}``,
    ``reasoning_effort``, …). Disabling therefore uses ``reasoning.enabled=false``
    rather than the OpenAI-native ``reasoning_effort`` "none" tier — the flat effort
    param has no portable "off" value across OpenRouter's open-weight models (e.g.
    Kimi only accepts low/medium/high), whereas ``reasoning.enabled=false`` disables
    uniformly. Everything else (URL, auth, sampler params) is inherited unchanged.
    """

    def _disable_reasoning(self, payload: dict[str, Any]) -> None:
        payload["reasoning"] = {"enabled": False}
        payload.pop("reasoning_effort", None)
