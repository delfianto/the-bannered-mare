"""Ollama adapter — extends OpenAI-compatible adapter with local-server defaults."""

from src.provider.adapters.openai import OpenAIAdapter


class OllamaAdapter(OpenAIAdapter):
    """Adapter for Ollama's OpenAI-compatible /v1/chat/completions endpoint."""

    def build_url(
        self,
        base_url: str,
        model: str,
        stream: bool,
        api_key: str | None = None,
    ) -> str:
        return f"{base_url}/v1/chat/completions"

    def build_headers(self, api_key: str | None) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    def get_timeout(self, model: str) -> float:
        return 300.0
