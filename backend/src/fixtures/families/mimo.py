"""Xiaomi MiMo model family seed data (base-model-generation keyed).

MiMo V2.5 and V2.5-Pro share the V2.5 generation: 1M context, 131K max output,
reasoning-capable. V2.5-Pro is the 1.02T MoE (42B active, hybrid attention); the
base V2.5 exposes a narrower sampler surface — top_k / min_p / repetition_penalty
are Pro-only, so they sit in the family schema (superset) but only the Pro seed
sets them. Recommended sampling: temperature 1.0 / top_p 0.95. Routed via
OpenRouter (also Xiaomi's MiMo platform directly).

Parameters per the Xiaomi MiMo docs (platform.xiaomimimo.com) + OpenRouter.
"""

from src.fixtures.model_families import ModelFamilySeedData
from src.fixtures.parameter_definitions import (
    FREQUENCY_PENALTY,
    PRESENCE_PENALTY,
    TEMPERATURE,
    TOP_K,
    TOP_P_95,
)

MIMO_FAMILIES: list[ModelFamilySeedData] = [
    {
        "name": "Xiaomi MiMo V2.5",
        "family_identifier": "xiaomi/mimo-v2.5",
        "description": (
            "Xiaomi MiMo V2.5 and V2.5-Pro. 1M context, 131K max output, reasoning-capable. "
            "Pro is a 1.02T MoE (42B active). top_k/min_p/repetition_penalty are Pro-only. "
            "Routed via OpenRouter."
        ),
        "provider_types": ["openrouter", "opencode", "opencode_go"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 4096, "min_value": 1, "max_value": 131072},
            "temperature": TEMPERATURE,
            "top_p": TOP_P_95,
            # top_k / min_p / repetition_penalty are MiMo-V2.5-Pro only.
            "top_k": {**TOP_K, "max_value": 100},
            "min_p": {"type": "float", "default": 0.0, "min_value": 0.0, "max_value": 1.0},
            "frequency_penalty": FREQUENCY_PENALTY,
            "presence_penalty": PRESENCE_PENALTY,
            "repetition_penalty": {
                "type": "float",
                "default": 1.0,
                "min_value": 1.0,
                "max_value": 2.0,
            },
        },
        "unsupported_parameters": [],
        "extra_metadata": {
            "lineage": "mimo",
            "developer": "xiaomi",
            "context_window": 1048576,
            "supports_vision": False,
            "supports_function_calling": True,
            "supports_reasoning": True,
            "note": (
                "V2.5-Pro is a 1.02T MoE (42B active); top_k/min_p/repetition_penalty are "
                "Pro-only. Recommended temp 1.0 / top_p 0.95."
            ),
            "models": ["xiaomi/mimo-v2.5", "xiaomi/mimo-v2.5-pro"],
        },
    },
]
