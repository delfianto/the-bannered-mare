"""OpenRouter long-tail model family.

The `misc` catch-all for OpenRouter models that don't (yet) warrant their own
base-model lineage file (Arcee, Qwen, Xiaomi, Poolside, etc.).
"""

from src.fixtures.model_families import ModelFamilySeedData
from src.fixtures.parameter_definitions import TEMPERATURE

OPENROUTER_FAMILIES: list[ModelFamilySeedData] = [
    {
        "name": "OpenRouter Misc",
        "family_identifier": "openrouter/misc",
        "description": "Various OpenRouter models",
        "provider_types": ["openrouter"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 4096, "min_value": 1, "max_value": 16384},
            "temperature": {**TEMPERATURE, "default": 0.8},
            "top_p": {"type": "float", "default": 0.9, "min_value": 0.0, "max_value": 1.0},
        },
        "extra_metadata": {
            "reasoning_mode": "none",
            "context_window": 128000,
            "supports_vision": False,
            "supports_function_calling": False,
        },
    },
]
