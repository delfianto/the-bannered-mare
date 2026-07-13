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
]
