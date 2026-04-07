"""xAI Grok model seed data."""

from src.fixtures.models._types import ModelSeedData

XAI_MODELS: list[ModelSeedData] = [
    {
        "name": "Grok 4.0",
        "model_identifier": "grok-4-0709",
        "openrouter_identifier": "x-ai/grok-4-0709",
        "family_identifier": "xai/grok-4",
        "provider_type": "xai",
        "parameters": {
            "max_completion_tokens": 2048,
            "temperature": 0.9,
            "top_p": 0.92,
        },
        "enabled": True,
        "use_openrouter": False,
    },
    {
        "name": "Grok 4.1 Fast",
        "model_identifier": "grok-4-1-fast-non-reasoning",
        "openrouter_identifier": "x-ai/grok-4.1-fast",
        "family_identifier": "xai/grok-4.1-fast",
        "provider_type": "xai",
        "parameters": {
            "max_completion_tokens": 4096,
            "temperature": 0.9,
            "top_p": 0.92,
        },
        "enabled": True,
        "use_openrouter": False,
    },
    {
        "name": "Grok 4.20",
        "model_identifier": "grok-4.20-0309-non-reasoning",
        "openrouter_identifier": "x-ai/grok-4.20",
        "family_identifier": "xai/grok-4.20",
        "provider_type": "xai",
        "parameters": {
            "max_completion_tokens": 4096,
            "temperature": 0.9,
            "top_p": 0.92,
        },
        "enabled": True,
        "use_openrouter": False,
    },
]
