"""MiniMax model family seed data (base-model-generation keyed).

Split at the M2 -> M3 contract break. MiniMax M2.5 / M2.7 (204K context) are
always-thinking (thinking cannot be disabled); M3 jumps to a 1M context with up
to 512K output and makes thinking toggleable (thinking={type: adaptive|disabled}).
The hosted MiniMax API does not accept top_k and ignores frequency/presence
penalties — all three are marked unsupported. temperature and top_p must both be
> 0 with a ceiling of 1.0 (temp=0 / top_p=0 error); recommended temp 1.0 /
top_p 0.95. Routed via OpenRouter.

Parameters per the MiniMax OpenAI-compatible API docs (platform.minimax.io).
"""

from src.fixtures.model_families import ModelFamilySeedData, NumericParameterSchema

# MiniMax caps temperature and top_p at 1.0 and requires both > 0 (temp=0 or
# top_p=0 error on the native API). min_value 0.01 approximates the exclusive
# lower bound our schema can't express.
_MINIMAX_TEMPERATURE: NumericParameterSchema = {
    "type": "float",
    "default": 1.0,
    "min_value": 0.01,
    "max_value": 1.0,
}
_MINIMAX_TOP_P: NumericParameterSchema = {
    "type": "float",
    "default": 0.95,
    "min_value": 0.01,
    "max_value": 1.0,
}

MINIMAX_FAMILIES: list[ModelFamilySeedData] = [
    {
        "name": "MiniMax M2",
        "family_identifier": "minimax/minimax-m2",
        "description": (
            "MiniMax M2.5 / M2.7. 204K context. Recommended temp 1.0 / top_p 0.95 / "
            "top_k 20-40. Thinking is always on (cannot be disabled). Routed via OpenRouter."
        ),
        "provider_types": ["openrouter", "opencode", "opencode_go"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 8192, "min_value": 1, "max_value": 131072},
            "temperature": _MINIMAX_TEMPERATURE,
            "top_p": _MINIMAX_TOP_P,
        },
        # The hosted API drops top_k and silently ignores the OpenAI penalties.
        "unsupported_parameters": ["top_k", "frequency_penalty", "presence_penalty"],
        "extra_metadata": {
            "reasoning_mode": "always_on",
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
        "provider_types": ["openrouter", "opencode", "opencode_go"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 8192, "min_value": 1, "max_value": 512000},
            "temperature": _MINIMAX_TEMPERATURE,
            "top_p": _MINIMAX_TOP_P,
            "thinking": {
                "type": "object",
                "properties": {
                    "type": {"type": "enum", "str_values": ["adaptive", "disabled"]},
                },
            },
        },
        "unsupported_parameters": ["top_k", "frequency_penalty", "presence_penalty"],
        "extra_metadata": {
            "reasoning_mode": "optional",
            "lineage": "minimax",
            "developer": "minimax",
            "context_window": 1048576,
            "supports_vision": False,
            "supports_function_calling": True,
            "models": ["minimax/minimax-m3"],
        },
    },
]
