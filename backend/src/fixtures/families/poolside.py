"""Poolside model family seed data.

Poolside's Laguna coding-agent models (M.1 flagship, XS.2 compact) — fp8-quantized,
tool calling + reasoning, 262K context / 32K max output. Narrow parameter surface:
only temperature + max_tokens are tuneable (no top_p / top_k / penalties / stop).
Free on OpenRouter for now; "good enough" and fun for experimentation.
"""

from src.fixtures.model_families import ModelFamilySeedData
from src.fixtures.parameter_definitions import TEMPERATURE

POOLSIDE_FAMILIES: list[ModelFamilySeedData] = [
    {
        "name": "Poolside Laguna",
        "family_identifier": "poolside/laguna",
        "description": (
            "Poolside Laguna coding-agent models (M.1 flagship, XS.2 compact). fp8-quantized, "
            "tool calling + reasoning, 262K context, 32K max output. Narrow sampler "
            "(temperature only). Free on OpenRouter for now."
        ),
        "provider_types": ["openrouter"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 4096, "min_value": 1, "max_value": 32768},
            "temperature": TEMPERATURE,
        },
        "unsupported_parameters": [
            "top_p",
            "top_k",
            "frequency_penalty",
            "presence_penalty",
            "stop",
        ],
        "extra_metadata": {
            "reasoning_mode": "optional",
            "lineage": "poolside",
            "developer": "poolside",
            "context_window": 262144,
            "supports_vision": False,
            "supports_function_calling": True,
            "supports_prompt_caching": True,
            "supports_reasoning": True,
            "note": "coding-agent models (fp8); free on OpenRouter for now",
            "models": ["poolside/laguna-m.1", "poolside/laguna-xs-2.1"],
        },
    },
]
