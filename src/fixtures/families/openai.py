"""OpenAI model family seed data."""

from src.fixtures.model_families import ModelFamilySeedData
from src.fixtures.parameter_definitions import (
    OPENAI_SAMPLING,
    OPENAI_THINKING_COMMON,
)

_UNSUPPORTED_THINKING = [
    "max_tokens",
    "temperature",
    "top_p",
    "frequency_penalty",
    "presence_penalty",
]

_UNSUPPORTED_CHAT = [
    "max_tokens",
    "reasoning_effort",
    "summary",
    "verbosity",
]


OPENAI_FAMILIES: list[ModelFamilySeedData] = [
    # GPT-4o chat-style
    {
        "name": "OpenAI GPT-4o",
        "family_identifier": "openai/gpt-4o",
        "description": "OpenAI GPT-4o family. 128K context, multimodal, classic sampling.",
        "provider_types": ["openai", "openrouter"],
        "parameters": {
            "max_completion_tokens": {
                "type": "int",
                "default": 4096,
                "min_value": 1,
                "max_value": 16384,
            },
            **OPENAI_SAMPLING,
        },
        "unsupported_parameters": _UNSUPPORTED_CHAT,
        "extra_metadata": {
            "context_window": 128000,
            "supports_vision": True,
            "supports_function_calling": True,
            "models": ["gpt-4o", "gpt-4o-mini"],
        },
    },
    # GPT-5.3 Chat
    {
        "name": "OpenAI GPT-5.3 Chat",
        "family_identifier": "openai/gpt-5.3-chat",
        "description": "OpenAI GPT-5.3 chat model. Standard sampling, no reasoning.",
        "provider_types": ["openai", "openrouter"],
        "parameters": {
            "max_completion_tokens": {
                "type": "int",
                "default": 8192,
                "min_value": 1,
                "max_value": 16384,
            },
            "summary": {
                "type": "enum",
                "default": "auto",
                "str_values": ["concise", "detailed", "auto"],
            },
            **OPENAI_SAMPLING,
        },
        "unsupported_parameters": ["reasoning_effort", "verbosity", "max_tokens"],
        "extra_metadata": {
            "context_window": 128000,
            "supports_vision": False,
            "supports_function_calling": True,
            "models": ["gpt-5.3-instant-2026-03-03"],
        },
    },
    # GPT-5.4 Thinking (reasoning models)
    {
        "name": "OpenAI GPT-5.4 Thinking",
        "family_identifier": "openai/gpt-5.4-thinking",
        "description": (
            "OpenAI GPT-5.4 reasoning models (Mar 2026). "
            "Extended thinking, up to 922K input context."
        ),
        "provider_types": ["openai", "openrouter"],
        "parameters": {
            "max_completion_tokens": {
                "type": "int",
                "default": 8192,
                "min_value": 1,
                "max_value": 128000,
            },
            "reasoning_effort": {
                "type": "enum",
                "default": "medium",
                "str_values": ["low", "medium", "high"],
            },
            **OPENAI_THINKING_COMMON,
            "summary": {
                "type": "enum",
                "default": "auto",
                "str_values": ["concise", "detailed", "auto"],
            },
        },
        "unsupported_parameters": _UNSUPPORTED_THINKING,
        "extra_metadata": {
            "context_window": 922000,
            "supports_vision": True,
            "supports_function_calling": True,
            "models": ["gpt-5.4-2026-03-05", "gpt-5.4-mini-2026-03-17", "gpt-5.4-nano-2026-03-17"],
        },
    },
]
