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
from src.provider.adapters.lmstudio import LMStudioAdapter
from src.provider.adapters.ollama import OllamaAdapter
from src.provider.adapters.openai import OpenAIAdapter
from src.provider.adapters.openrouter import OpenRouterAdapter

_REGISTRY: dict[ProviderType, type[ProviderAdapter]] = {
    ProviderType.OPENAI: OpenAIAdapter,
    ProviderType.ANTHROPIC: AnthropicAdapter,
    ProviderType.GOOGLE: GeminiAdapter,
    ProviderType.XAI: OpenAIAdapter,
    ProviderType.OPENROUTER: OpenRouterAdapter,
    ProviderType.OLLAMA: OllamaAdapter,
    ProviderType.LMSTUDIO: LMStudioAdapter,
    ProviderType.OPENCODE: OpenAIAdapter,
    ProviderType.OPENCODE_GO: OpenAIAdapter,
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
