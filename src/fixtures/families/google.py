"""Google Gemini model family seed data."""

from src.fixtures.model_families import ModelFamilySeedData
from src.fixtures.parameter_definitions import GEMINI_SAMPLING

GOOGLE_FAMILIES: list[ModelFamilySeedData] = [
    {
        "name": "Gemini 2.5",
        "family_identifier": "google/gemini-2.5",
        "description": "Google Gemini 2.5 Flash & Pro. 1M context, implicit caching.",
        "provider_types": ["google", "openrouter"],
        "parameters": {
            "max_output_tokens": {
                "type": "int",
                "default": 8192,
                "min_value": 1,
                "max_value": 65536,
            },
            **GEMINI_SAMPLING,
        },
        "extra_metadata": {
            "context_window": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "models": ["gemini-2.5-flash", "gemini-2.5-pro"],
        },
    },
    {
        "name": "Gemini 3 (Preview)",
        "family_identifier": "google/gemini-3-preview",
        "description": (
            "Google Gemini 3 Flash & 3.1 Pro (preview). Configurable thinking levels. 1M context."
        ),
        "provider_types": ["google", "openrouter"],
        "parameters": {
            "max_output_tokens": {
                "type": "int",
                "default": 8192,
                "min_value": 1,
                "max_value": 65536,
            },
            **GEMINI_SAMPLING,
            "thinking_level": {
                "type": "enum",
                "default": "minimal",
                "str_values": ["minimal", "low", "medium", "high"],
            },
        },
        "extra_metadata": {
            "context_window": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "models": ["gemini-3-flash-preview", "gemini-3.1-pro-preview"],
        },
    },
]
