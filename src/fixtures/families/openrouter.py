"""OpenRouter-specific model family seed data.

Parameter ranges/defaults below follow each vendor's documented sampling guidance:
DeepSeek (temp default 1.0, reasoner ignores temp/top_p), Moonshot Kimi K2
(thinking temp ~1.0 / instant ~0.6, 256K ctx), Zhipu GLM (temp 0-1, thinking
auto, 200K ctx), MiniMax M2 (temp 1.0 / top_p 0.95 / top_k 20-40, 204K ctx).
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
        "name": "DeepSeek General",
        "family_identifier": "openrouter/deepseek",
        "description": "DeepSeek V3.1/V3.2/V4 chat + R1 reasoner. Note: the reasoner ignores temperature/top_p.",
        "provider_types": ["openrouter"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 4096, "min_value": 1, "max_value": 65536},
            "temperature": {"type": "float", "default": 1.0, "min_value": 0.0, "max_value": 2.0},
            "top_p": {"type": "float", "default": 0.95, "min_value": 0.0, "max_value": 1.0},
            "frequency_penalty": {
                "type": "float",
                "default": 0.0,
                "min_value": -2.0,
                "max_value": 2.0,
            },
            "presence_penalty": {
                "type": "float",
                "default": 0.0,
                "min_value": -2.0,
                "max_value": 2.0,
            },
        },
        "extra_metadata": {
            "context_window": 128000,
            "supports_vision": False,
            "supports_function_calling": True,
        },
    },
    {
        "name": "GLM General",
        "family_identifier": "openrouter/glm",
        "description": "Zhipu GLM 4.7/5 family. Thinking mode auto-enabled; temperature capped at 1.0.",
        "provider_types": ["openrouter"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 4096, "min_value": 1, "max_value": 128000},
            "temperature": {"type": "float", "default": 0.8, "min_value": 0.0, "max_value": 1.0},
            "top_p": {"type": "float", "default": 0.95, "min_value": 0.0, "max_value": 1.0},
            "thinking": {
                "type": "enum",
                "default": "enabled",
                "str_values": ["enabled", "disabled"],
            },
        },
        "extra_metadata": {
            "context_window": 200000,
            "supports_vision": False,
            "supports_function_calling": True,
        },
    },
    {
        "name": "MiniMax General",
        "family_identifier": "openrouter/minimax",
        "description": "MiniMax M2/M3 series. Recommended temp 1.0 / top_p 0.95 / top_k 40.",
        "provider_types": ["openrouter"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 4096, "min_value": 1, "max_value": 65536},
            "temperature": {"type": "float", "default": 1.0, "min_value": 0.0, "max_value": 2.0},
            "top_p": {"type": "float", "default": 0.95, "min_value": 0.0, "max_value": 1.0},
            "top_k": {"type": "int", "default": 40, "min_value": 1, "max_value": 100},
        },
        "extra_metadata": {
            "context_window": 204800,
            "supports_vision": False,
            "supports_function_calling": True,
        },
    },
    {
        "name": "Kimi (Moonshot)",
        "family_identifier": "openrouter/kimi",
        "description": "Moonshot Kimi K2 series. Thinking mode ~temp 1.0, instant ~temp 0.6. 256K context.",
        "provider_types": ["openrouter"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 8192, "min_value": 1, "max_value": 65536},
            "temperature": {"type": "float", "default": 0.6, "min_value": 0.0, "max_value": 2.0},
            "top_p": {"type": "float", "default": 1.0, "min_value": 0.0, "max_value": 1.0},
        },
        "extra_metadata": {
            "context_window": 256000,
            "supports_vision": False,
            "supports_function_calling": True,
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
