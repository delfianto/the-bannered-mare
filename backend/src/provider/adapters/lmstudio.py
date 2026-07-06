"""LM Studio adapter — OpenAI-compatible local server (default port 1234)."""

from src.provider.adapters.openai import OpenAIAdapter


def strip_v1_suffix(base_url: str) -> str:
    """Strip a trailing ``/v1`` from a base URL.

    Users commonly configure LM Studio's base_url with an OpenAI-SDK-style
    ``/v1`` suffix already included. Both the OpenAI-compatible chat endpoint
    and LM Studio's native ``/api/v1/...`` endpoints need the bare host, so
    this normalization is shared rather than duplicated per call site.
    """
    clean_url = base_url.rstrip("/")
    if clean_url.endswith("/v1"):
        clean_url = clean_url[:-3]
    return clean_url


class LMStudioAdapter(OpenAIAdapter):
    """Adapter for LM Studio's OpenAI-compatible ``/v1/chat/completions`` endpoint.

    LM Studio runs a local server (default ``http://localhost:1234``) exposing an
    OpenAI-compatible API. Auth is optional — LM Studio 0.4.0+ supports API
    tokens, so headers are inherited from ``OpenAIAdapter`` (a Bearer token is
    sent only when one is configured; local default sends none).
    """

    def build_url(
        self,
        base_url: str,
        model: str,
        stream: bool,
        api_key: str | None = None,
    ) -> str:
        return f"{strip_v1_suffix(base_url)}/v1/chat/completions"

    def get_timeout(self, model: str) -> float:
        # Local inference can be slow on first load / large models.
        return 300.0
