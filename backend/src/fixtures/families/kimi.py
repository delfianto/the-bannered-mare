"""Moonshot Kimi model family seed data (base-model-generation keyed).

Kimi K2.5 and K2.6 share one OpenAI/Anthropic-compatible contract (256K context,
full sampling surface + reasoning_effort), so they live in a single kimi-k2
family. Thinking mode runs ~temperature 1.0 and instant mode ~0.6; set
max_tokens >= 16000 to leave room for reasoning_content. Routed via OpenRouter.

Parameters per the Moonshot/Kimi platform docs (platform.moonshot.ai).
"""

from src.fixtures.model_families import ModelFamilySeedData
from src.fixtures.parameter_definitions import (
    FREQUENCY_PENALTY,
    PRESENCE_PENALTY,
    TOP_P_95,
)

KIMI_FAMILIES: list[ModelFamilySeedData] = [
    {
        "name": "Kimi K2",
        "family_identifier": "moonshot/kimi-k2",
        "description": (
            "Moonshot Kimi K2.5 / K2.6 (OpenAI/Anthropic-compatible). 256K context, full "
            "sampling surface plus reasoning_effort. Routed via OpenRouter."
        ),
        "provider_types": ["openrouter"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 8192, "min_value": 1, "max_value": 65536},
            # Moonshot caps temperature at 1.0 (not 2.0). Thinking mode wants ~1.0,
            # instant mode ~0.6 (the RP-fast default).
            "temperature": {"type": "float", "default": 0.6, "min_value": 0.0, "max_value": 1.0},
            "top_p": TOP_P_95,
            "frequency_penalty": FREQUENCY_PENALTY,
            "presence_penalty": PRESENCE_PENALTY,
            "reasoning_effort": {
                "type": "enum",
                "default": "medium",
                "str_values": ["low", "medium", "high"],
            },
        },
        # Moonshot's contract has no top_k/min_p/repetition_penalty (even its
        # first-party OpenRouter endpoint omits them).
        "unsupported_parameters": ["top_k"],
        "extra_metadata": {
            "lineage": "kimi",
            "developer": "moonshot",
            "context_window": 262144,
            "supports_vision": False,
            "supports_function_calling": True,
            "note": "thinking ~temp 1.0, instant ~temp 0.6; max_tokens >= 16000 for full reasoning",
            "models": ["moonshotai/kimi-k2.5", "moonshotai/kimi-k2.6"],
        },
    },
]
