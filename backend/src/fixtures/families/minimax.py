"""MiniMax model family seed data (base-model-generation keyed).

Split at the M2 -> M3 contract break. MiniMax M2.5 / M2.7 (204K context) keep
top_k and are always-thinking (thinking cannot be disabled). MiniMax M3 jumps to
a 1M context with up to 512K output, drops top_k, and makes thinking toggleable
(thinking={type: adaptive|disabled}). MiniMax ignores frequency/presence
penalties. temperature range [0, 2] (out-of-range errors), recommended 1.0.
Routed via OpenRouter.

Parameters per the MiniMax OpenAI-compatible API docs (platform.minimax.io).
"""

from src.fixtures.model_families import ModelFamilySeedData
from src.fixtures.parameter_definitions import TEMPERATURE, TOP_K, TOP_P_95

MINIMAX_FAMILIES: list[ModelFamilySeedData] = [
    {
        "name": "MiniMax M2",
        "family_identifier": "minimax/minimax-m2",
        "description": (
            "MiniMax M2.5 / M2.7. 204K context. Recommended temp 1.0 / top_p 0.95 / "
            "top_k 20-40. Thinking is always on (cannot be disabled). Routed via OpenRouter."
        ),
        "provider_types": ["openrouter"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 8192, "min_value": 1, "max_value": 131072},
            "temperature": TEMPERATURE,
            "top_p": TOP_P_95,
            "top_k": {**TOP_K, "max_value": 100},
        },
        # MiniMax silently ignores the OpenAI penalties.
        "unsupported_parameters": ["frequency_penalty", "presence_penalty"],
        "extra_metadata": {
            "lineage": "minimax",
            "developer": "minimax",
            "context_window": 204800,
            "supports_vision": False,
            "supports_function_calling": True,
            "thinking_behavior": "always on (cannot be disabled)",
            "models": ["minimax/minimax-m2.5", "minimax/minimax-m2.7"],
        },
    },
    {
        "name": "MiniMax M3",
        "family_identifier": "minimax/minimax-m3",
        "description": (
            "MiniMax M3. 1M context, up to 512K output. Toggleable thinking "
            "(adaptive/disabled); top_k and penalties removed. Routed via OpenRouter."
        ),
        "provider_types": ["openrouter"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 8192, "min_value": 1, "max_value": 512000},
            "temperature": TEMPERATURE,
            "top_p": TOP_P_95,
            "thinking": {
                "type": "object",
                "properties": {
                    "type": {"type": "enum", "str_values": ["adaptive", "disabled"]},
                },
            },
        },
        "unsupported_parameters": ["top_k", "frequency_penalty", "presence_penalty"],
        "extra_metadata": {
            "lineage": "minimax",
            "developer": "minimax",
            "context_window": 1048576,
            "supports_vision": False,
            "supports_function_calling": True,
            "models": ["minimax/minimax-m3"],
        },
    },
]
