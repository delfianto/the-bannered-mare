"""Claude Sonnet tier family seed data.

Sonnet is Anthropic's balanced speed/intelligence tier. Split per generation:
4.5 uses an explicit thinking budget (`CLAUDE_45_BASE`); 4.6 moved to adaptive
thinking with an `effort` enum (`CLAUDE_46_BASE`). 4.5 Sonnet was previously
bundled with Haiku as `claude-4.5-standard`. Runs on the Anthropic API or via
OpenRouter.
"""

from src.fixtures.model_families import ModelFamilySeedData
from src.fixtures.parameter_definitions import CLAUDE_45_BASE, CLAUDE_46_BASE

CLAUDE_SONNET_FAMILIES: list[ModelFamilySeedData] = [
    {
        "name": "Claude 4.5 Sonnet",
        "family_identifier": "anthropic/claude-sonnet-4.5",
        "description": "Anthropic Claude 4.5 Sonnet. Balanced speed/intelligence for RP.",
        "provider_types": ["anthropic", "openrouter"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 4096, "min_value": 1, "max_value": 16384},
            **CLAUDE_45_BASE,
        },
        "unsupported_parameters": [],
        "extra_metadata": {
            "lineage": "claude-sonnet",
            "context_window": 500000,
            "supports_vision": True,
            "supports_function_calling": True,
            "models": ["claude-4.5-sonnet"],
        },
    },
    {
        "name": "Claude 4.6 Sonnet",
        "family_identifier": "anthropic/claude-sonnet-4.6",
        "description": "Anthropic Claude 4.6 Sonnet. Fast, high-intelligence with adaptive thinking.",
        "provider_types": ["anthropic", "openrouter"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 8192, "min_value": 1, "max_value": 64000},
            "effort": {
                "type": "enum",
                "default": "high",
                "str_values": ["low", "medium", "high", "max"],
            },
            **CLAUDE_46_BASE,
        },
        "unsupported_parameters": [],
        "extra_metadata": {
            "lineage": "claude-sonnet",
            "context_window": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "models": ["claude-4.6-sonnet"],
        },
    },
]
