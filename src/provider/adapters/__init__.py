"""Provider adapter registry."""

from src.core.persistence.enums import ProviderType
from src.provider.adapters.anthropic import AnthropicAdapter
from src.provider.adapters.base import (
    CompletionResponse,
    ProviderAdapter,
    StreamChunk,
    TokenUsage,
)
from src.provider.adapters.gemini import GeminiAdapter
from src.provider.adapters.ollama import OllamaAdapter
from src.provider.adapters.openai import OpenAIAdapter

_REGISTRY: dict[ProviderType, type[ProviderAdapter]] = {
    ProviderType.OPENAI: OpenAIAdapter,
    ProviderType.ANTHROPIC: AnthropicAdapter,
    ProviderType.GOOGLE: GeminiAdapter,
    ProviderType.XAI: OpenAIAdapter,
    ProviderType.OPENROUTER: OpenAIAdapter,
    ProviderType.OLLAMA: OllamaAdapter,
    ProviderType.CUSTOM: OpenAIAdapter,
}


def get_adapter(provider_type: ProviderType) -> ProviderAdapter:
    """Instantiate the correct adapter for a provider type."""
    cls = _REGISTRY.get(provider_type, OpenAIAdapter)
    return cls()


__all__ = [
    "CompletionResponse",
    "ProviderAdapter",
    "StreamChunk",
    "TokenUsage",
    "get_adapter",
]
