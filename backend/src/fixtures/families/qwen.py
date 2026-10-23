"""Alibaba Qwen model family seed data (base-model-generation keyed).

Qwen3.x commercial tier (Max / Plus) served over an OpenAI-compatible API. It
keeps the full OpenAI sampling surface — temperature up to 2.0, top_p, top_k, and
the frequency/presence penalties — and adds a hybrid thinking mode exposed
natively as ``enable_thinking`` rather than as a sampler. Served via OpenCode
Go / Zen and OpenRouter.

Parameters per the Alibaba Model Studio / DashScope OpenAI-compatible docs.
"""

from src.fixtures.model_families import ModelFamilySeedData
from src.fixtures.parameter_definitions import (
    FREQUENCY_PENALTY,
    PRESENCE_PENALTY,
    TEMPERATURE,
    TOP_K,
    TOP_P_95,
)

QWEN_FAMILIES: list[ModelFamilySeedData] = [
    {
        "name": "Qwen3",
        "family_identifier": "qwen/qwen3",
        "description": (
            "Alibaba Qwen3.x commercial tier (Qwen3.7 Max / Plus, Qwen3.6 Plus). "
            "OpenAI-compatible sampling with a hybrid thinking mode. Served via "
            "OpenCode Go / Zen and OpenRouter."
        ),
        "provider_types": ["openrouter", "opencode", "opencode_go"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 8192, "min_value": 1, "max_value": 131072},
            "temperature": TEMPERATURE,
            "top_p": TOP_P_95,
            "top_k": TOP_K,
            "frequency_penalty": FREQUENCY_PENALTY,
            "presence_penalty": PRESENCE_PENALTY,
        },
        "unsupported_parameters": [],
        "extra_metadata": {
            "reasoning_mode": "optional",
            "lineage": "qwen",
            "developer": "alibaba",
            "context_window": 262144,
            "supports_vision": False,
            "supports_function_calling": True,
            "supports_prompt_caching": True,
            "thinking_behavior": "hybrid; native enable_thinking toggle",
            "models": ["qwen3.7-max", "qwen3.7-plus", "qwen3.6-plus"],
        },
    },
    # Catalog refresh: 2026-10-23; https://openrouter.ai/api/v1/models
    {
        "name": "Qwen3.7 Max",
        "family_identifier": "qwen/qwen3.7-max",
        "description": "Qwen3.7 Max. Hosted text generation with model limits verified against the "
        "OpenRouter catalog (2026-10-23).",
        "provider_types": ["openrouter"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 8192, "min_value": 1, "max_value": 131072},
            "temperature": {"type": "float", "default": 1.0, "min_value": 0.0, "max_value": 2.0},
            "top_p": {"type": "float", "default": 0.95, "min_value": 0.0, "max_value": 1.0},
            "top_k": {"type": "int", "default": 40, "min_value": 1},
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
        "unsupported_parameters": [],
        "extra_metadata": {
            "reasoning_mode": "optional",
            "lineage": "qwen",
            "developer": "alibaba",
            "context_window": 1000000,
            "supports_vision": False,
            "supports_function_calling": True,
            "supports_prompt_caching": True,
            "models": ["qwen/qwen3.7-max"],
        },
    },
    {
        "name": "Qwen3.7 Plus",
        "family_identifier": "qwen/qwen3.7-plus",
        "description": "Qwen3.7 Plus. Hosted text generation with model limits verified against the "
        "OpenRouter catalog (2026-10-23).",
        "provider_types": ["openrouter", "opencode_go"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 8192, "min_value": 1, "max_value": 131072},
            "temperature": {"type": "float", "default": 1.0, "min_value": 0.0, "max_value": 2.0},
            "top_p": {"type": "float", "default": 0.95, "min_value": 0.0, "max_value": 1.0},
            "top_k": {"type": "int", "default": 40, "min_value": 1},
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
        "unsupported_parameters": [],
        "extra_metadata": {
            "reasoning_mode": "optional",
            "lineage": "qwen",
            "developer": "alibaba",
            "context_window": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "supports_prompt_caching": True,
            "models": ["qwen/qwen3.7-plus", "qwen3.7-plus"],
        },
    },
    {
        "name": "Qwen3.8",
        "family_identifier": "qwen/qwen3.8",
        "description": "Qwen3.8. Hosted text generation with model limits verified against the OpenRouter "
        "catalog (2026-10-23).",
        "provider_types": ["openrouter", "opencode_go"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 8192, "min_value": 1, "max_value": 131072},
            "temperature": {"type": "float", "default": 1.0, "min_value": 0.0, "max_value": 2.0},
            "top_p": {"type": "float", "default": 0.95, "min_value": 0.0, "max_value": 1.0},
            "top_k": {"type": "int", "default": 40, "min_value": 1},
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
        "unsupported_parameters": [],
        "extra_metadata": {
            "reasoning_mode": "optional",
            "lineage": "qwen",
            "developer": "alibaba",
            "context_window": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "supports_prompt_caching": True,
            "models": [
                "qwen/qwen3.8-max-0902",
                "qwen/qwen3.8-flash",
                "qwen3.8-max",
                "qwen3.8-flash",
            ],
        },
    },
]
