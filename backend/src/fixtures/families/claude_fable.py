"""Claude Fable tier family seed data.

Fable 5 is Anthropic's most capable tier (above Opus). Same request surface as
Opus 4.8 — adaptive thinking only, no sampling parameters — with one extra
constraint: thinking cannot be disabled (a `disabled` request 400s), so the only
mode is `adaptive`. Premium pricing; the deliberately over-powered option.
"""

from src.fixtures.model_families import ModelFamilySeedData
from src.fixtures.parameter_definitions import STOP_LIST, STREAM

CLAUDE_FABLE_FAMILIES: list[ModelFamilySeedData] = [
    {
        "name": "Claude Fable 5",
        "family_identifier": "anthropic/claude-fable-5",
        "description": (
            "Anthropic Claude Fable 5. Most powerful tier (above Opus). Adaptive thinking "
            "only — sampling parameters removed and thinking cannot be disabled."
        ),
        "provider_types": ["anthropic", "openrouter", "opencode"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 8192, "min_value": 1, "max_value": 128000},
            "effort": {
                "type": "enum",
                "default": "high",
                "str_values": ["low", "medium", "high", "xhigh", "max"],
            },
            "stop_sequences": STOP_LIST,
            "stream": STREAM,
            "system": {"type": "string"},
            # Fable 5 cannot disable thinking (a `disabled` request 400s) — adaptive only.
            "thinking": {
                "type": "object",
                "properties": {
                    "type": {"type": "enum", "str_values": ["adaptive"]},
                },
            },
            "metadata": {"type": "object"},
        },
        "unsupported_parameters": ["temperature", "top_p", "top_k", "budget_tokens"],
        "extra_metadata": {
            "reasoning_mode": "optional",
            "lineage": "claude-fable",
            "context_window": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "models": ["claude-fable-5"],
        },
    },
]
