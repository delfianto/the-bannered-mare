"""OpenRouter long-tail model families.

Small / catch-all buckets not yet promoted to their own base-model lineage:
Llama 3 RP finetunes (e.g. Euryale) and a misc grab-bag (Arcee, Qwen, etc.).
"""

from src.fixtures.model_families import ModelFamilySeedData
from src.fixtures.parameter_definitions import TEMPERATURE

OPENROUTER_FAMILIES: list[ModelFamilySeedData] = [
    {
        "name": "Llama 3 RP",
        "family_identifier": "openrouter/llama-3-rp",
        "description": "Llama 3 70B models optimized for creative roleplay scenarios",
        "provider_types": ["openrouter"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 4096, "min_value": 1, "max_value": 32768},
            "temperature": {**TEMPERATURE, "default": 0.8},
            "top_p": {"type": "float", "default": 0.9, "min_value": 0.0, "max_value": 1.0},
        },
        "extra_metadata": {
            "context_window": 8192,
            "supports_vision": False,
            "supports_function_calling": False,
        },
    },
    {
        "name": "OpenRouter Misc",
        "family_identifier": "openrouter/misc",
        "description": "Various OpenRouter models (Arcee, Qwen, Xiaomi, Poolside)",
        "provider_types": ["openrouter"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 4096, "min_value": 1, "max_value": 16384},
            "temperature": {**TEMPERATURE, "default": 0.8},
            "top_p": {"type": "float", "default": 0.9, "min_value": 0.0, "max_value": 1.0},
        },
        "extra_metadata": {
            "context_window": 128000,
            "supports_vision": False,
            "supports_function_calling": False,
        },
    },
]
