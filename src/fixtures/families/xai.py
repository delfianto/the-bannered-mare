"""xAI Grok model family seed data."""

from src.fixtures.model_families import ModelFamilySeedData
from src.fixtures.parameter_definitions import XAI_BASE

_UNSUPPORTED_REASONING = ["stop", "frequency_penalty", "presence_penalty", "reasoning_effort"]

GROK_FAMILIES: list[ModelFamilySeedData] = [
    {
        "name": "xAI Grok 4.0",
        "family_identifier": "xai/grok-4",
        "description": (
            "xAI Grok 4.0 (July 2025). Always-on reasoning, 256K context. "
            "Does not support stop sequences or penalties."
        ),
        "provider_types": ["xai", "openrouter"],
        "parameters": {
            "max_completion_tokens": {
                "type": "int",
                "default": 2048,
                "min_value": 1,
                "max_value": 256000,
            },
            **XAI_BASE,
        },
        "unsupported_parameters": _UNSUPPORTED_REASONING,
        "extra_metadata": {
            "context_window": 256000,
            "supports_vision": True,
            "supports_function_calling": True,
            "models": ["grok-4-0709"],
        },
    },
    {
        "name": "xAI Grok 4.1 Fast",
        "family_identifier": "xai/grok-4.1-fast",
        "description": (
            "xAI Grok 4.1 Fast (Feb 2026). 2M context, 30K max output. "
            "Ultra-cheap. Non-reasoning variant supports penalties/stop."
        ),
        "provider_types": ["xai", "openrouter"],
        "parameters": {
            "max_completion_tokens": {
                "type": "int",
                "default": 4096,
                "min_value": 1,
                "max_value": 30000,
            },
            **XAI_BASE,
        },
        "unsupported_parameters": [],
        "extra_metadata": {
            "context_window": 2000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "models": ["grok-4-1-fast-non-reasoning", "grok-4-1-fast-reasoning"],
        },
    },
    {
        "name": "xAI Grok 4.20",
        "family_identifier": "xai/grok-4.20",
        "description": (
            "xAI Grok 4.20 (Mar 2026). Latest flagship. 2M context. "
            "Reasoning and non-reasoning variants."
        ),
        "provider_types": ["xai", "openrouter"],
        "parameters": {
            "max_completion_tokens": {
                "type": "int",
                "default": 4096,
                "min_value": 1,
                "max_value": 2000000,
            },
            **XAI_BASE,
        },
        "unsupported_parameters": [],
        "extra_metadata": {
            "context_window": 2000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "models": [
                "grok-4.20-0309-non-reasoning",
                "grok-4.20-0309-reasoning",
            ],
        },
    },
]

XAI_FAMILIES = GROK_FAMILIES
