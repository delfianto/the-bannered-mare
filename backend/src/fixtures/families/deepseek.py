"""DeepSeek model family seed data (base-model keyed).

The DeepSeek lineup is one tightly-coupled vendor lineage, so it lives in a
single file with one record per base model. V3 and V4 are chat models sharing a
sampling contract; R1 is the reasoner, which ignores temperature/top_p and
penalties (declared in ``unsupported_parameters``). This replaces the former
provider-keyed ``openrouter/deepseek`` record that conflated chat + reasoner.
"""

from src.fixtures.model_families import ModelFamilySeedData
from src.fixtures.parameter_definitions import (
    FREQUENCY_PENALTY,
    PRESENCE_PENALTY,
    TEMPERATURE,
    TOP_P_95,
)

# Shared chat sampling contract for the V3/V4 generations.
_DEEPSEEK_CHAT: dict = {
    "temperature": TEMPERATURE,
    "top_p": TOP_P_95,
    "frequency_penalty": FREQUENCY_PENALTY,
    "presence_penalty": PRESENCE_PENALTY,
}

DEEPSEEK_FAMILIES: list[ModelFamilySeedData] = [
    {
        "name": "DeepSeek V3",
        "family_identifier": "deepseek/deepseek-v3",
        "description": "DeepSeek V3.1 / V3.2 chat models. 128K context, standard sampling.",
        "provider_types": ["openrouter", "opencode", "opencode_go"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 4096, "min_value": 1, "max_value": 65536},
            **_DEEPSEEK_CHAT,
        },
        "unsupported_parameters": [],
        "extra_metadata": {
            # V3.1 introduced hybrid think/non-think; V3.2 is reasoning-first. Both
            # let the caller disable thinking (deepseek-chat id / thinking toggle).
            "reasoning_mode": "optional",
            "lineage": "deepseek",
            "context_window": 128000,
            "supports_vision": False,
            "supports_function_calling": True,
            "models": ["deepseek/deepseek-chat-v3.1", "deepseek/deepseek-v3.2"],
        },
    },
    {
        "name": "DeepSeek V4",
        "family_identifier": "deepseek/deepseek-v4",
        "description": "DeepSeek V4 chat models (Pro / Flash). 128K context, standard sampling.",
        "provider_types": ["openrouter", "opencode", "opencode_go"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 4096, "min_value": 1, "max_value": 65536},
            **_DEEPSEEK_CHAT,
        },
        "unsupported_parameters": [],
        "extra_metadata": {
            # V4 Pro/Flash are unified hybrid (Thinking / Non-Thinking dual modes);
            # thinking is caller-disablable via the thinking toggle / reasoning_effort.
            "reasoning_mode": "optional",
            "lineage": "deepseek",
            "context_window": 128000,
            "supports_vision": False,
            "supports_function_calling": True,
            "models": ["deepseek/deepseek-v4-pro", "deepseek/deepseek-v4-flash"],
        },
    },
    {
        "name": "DeepSeek R1",
        "family_identifier": "deepseek/deepseek-r1",
        "description": (
            "DeepSeek R1 reasoner. Thinking model — temperature/top_p and penalties are "
            "ignored by the API."
        ),
        "provider_types": ["openrouter", "opencode", "opencode_go"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 8192, "min_value": 1, "max_value": 65536},
        },
        # The reasoner silently ignores these; surface that rather than pretend support.
        "unsupported_parameters": ["temperature", "top_p", "frequency_penalty", "presence_penalty"],
        "extra_metadata": {
            "reasoning_mode": "always_on",
            "lineage": "deepseek",
            "context_window": 128000,
            "supports_vision": False,
            "supports_function_calling": True,
            "models": ["deepseek/deepseek-r1"],
        },
    },
]
