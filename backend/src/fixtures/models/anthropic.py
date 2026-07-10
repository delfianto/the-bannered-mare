"""Anthropic model seed data."""

from src.fixtures.models._types import ModelSeedData

ANTHROPIC_MODELS: list[ModelSeedData] = [
    {
        "name": "Claude 4.5 Haiku",
        "model_identifier": "claude-haiku-4-5",
        "family_identifier": "anthropic/claude-haiku-4.5",
        "provider_type": "anthropic",
        "parameters": {
            "max_tokens": 4096,
            "temperature": 0.85,
            "top_k": 60,
            "thinking": {"type": "disabled"},
        },
        "enabled": True,
    },
    {
        "name": "Claude 4.5 Sonnet",
        "model_identifier": "claude-sonnet-4-5",
        "family_identifier": "anthropic/claude-sonnet-4.5",
        "provider_type": "anthropic",
        "parameters": {
            "max_tokens": 8192,
            "temperature": 0.85,
            "top_k": 60,
            "thinking": {"type": "disabled"},
        },
        "enabled": True,
    },
    {
        "name": "Claude 4.5 Opus",
        "model_identifier": "claude-opus-4-5",
        "family_identifier": "anthropic/claude-opus-4.5",
        "provider_type": "anthropic",
        "parameters": {
            "max_tokens": 16384,
            "temperature": 0.85,
            "top_k": 60,
            "thinking": {"type": "disabled"},
        },
        "enabled": True,
    },
    {
        "name": "Claude 4.6 Sonnet",
        "model_identifier": "claude-sonnet-4-6",
        "family_identifier": "anthropic/claude-sonnet-4.6",
        "provider_type": "anthropic",
        "parameters": {
            "max_tokens": 8192,
            "temperature": 0.85,
            "top_k": 60,
            "effort": "low",
            "thinking": {"type": "disabled"},
        },
        "enabled": True,
    },
    {
        "name": "Claude 4.6 Opus",
        "model_identifier": "claude-opus-4-6",
        "family_identifier": "anthropic/claude-opus-4.6",
        "provider_type": "anthropic",
        "parameters": {
            "max_tokens": 16384,
            "temperature": 0.85,
            "top_k": 60,
            "effort": "low",
            "thinking": {"type": "disabled"},
        },
        "enabled": True,
    },
    {
        "name": "Claude 4.7 Opus",
        "model_identifier": "claude-opus-4-7",
        "family_identifier": "anthropic/claude-opus-4.7",
        "provider_type": "anthropic",
        "parameters": {
            "max_tokens": 16384,
            "effort": "low",
            "thinking": {"type": "disabled"},
        },
        "enabled": True,
    },
    {
        "name": "Claude 4.8 Opus",
        "model_identifier": "claude-opus-4-8",
        "family_identifier": "anthropic/claude-opus-4.8",
        "provider_type": "anthropic",
        "parameters": {
            "max_tokens": 16384,
            "effort": "low",
            "thinking": {"type": "disabled"},
        },
        "enabled": True,
    },
    {
        "name": "Claude Sonnet 5",
        "model_identifier": "claude-sonnet-5",
        "family_identifier": "anthropic/claude-sonnet-5",
        "provider_type": "anthropic",
        "parameters": {
            "max_tokens": 8192,
            "effort": "low",
            "thinking": {"type": "disabled"},
        },
        "enabled": True,
    },
    {
        "name": "Claude Fable 5",
        "model_identifier": "claude-fable-5",
        "family_identifier": "anthropic/claude-fable-5",
        "provider_type": "anthropic",
        "parameters": {
            "max_tokens": 16384,
            "effort": "low",
            "thinking": {"type": "adaptive"},
        },
        "enabled": True,
    },
]
