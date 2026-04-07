"""OpenRouter-specific model family seed data."""

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
        "name": "DeepSeek General",
        "family_identifier": "openrouter/deepseek",
        "description": "DeepSeek V3/V3.2 chat and reasoning models",
        "provider_types": ["openrouter"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 4096, "min_value": 1, "max_value": 16384},
            "temperature": {"type": "float", "default": 0.7, "min_value": 0.0, "max_value": 1.5},
        },
        "extra_metadata": {
            "context_window": 64000,
            "supports_vision": False,
            "supports_function_calling": True,
        },
    },
    {
        "name": "GLM General",
        "family_identifier": "openrouter/glm",
        "description": "Zhipu GLM family models (GLM-4.7, GLM-5)",
        "provider_types": ["openrouter"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 4096, "min_value": 1, "max_value": 8192},
            "temperature": {"type": "float", "default": 0.7, "min_value": 0.0, "max_value": 1.0},
        },
        "extra_metadata": {
            "context_window": 128000,
            "supports_vision": True,
            "supports_function_calling": False,
        },
    },
    {
        "name": "MiniMax General",
        "family_identifier": "openrouter/minimax",
        "description": "MiniMax M2 family models",
        "provider_types": ["openrouter"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 4096, "min_value": 1, "max_value": 16384},
            "temperature": {"type": "float", "default": 0.8, "min_value": 0.0, "max_value": 1.0},
        },
        "extra_metadata": {
            "context_window": 128000,
            "supports_vision": False,
            "supports_function_calling": False,
        },
    },
    {
        "name": "OpenRouter Misc",
        "family_identifier": "openrouter/misc",
        "description": "Various OpenRouter models (Arcee, Moonshot, Qwen, Xiaomi)",
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
