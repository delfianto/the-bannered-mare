"""Claude Haiku tier family seed data.

Haiku is Anthropic's fast/low-cost tier. 4.5 shares the 4.5 parameter contract
(`CLAUDE_45_BASE`) and was previously bundled with Sonnet as
`claude-4.5-standard`. Runs on the Anthropic API or via OpenRouter.
"""

from src.fixtures.model_families import ModelFamilySeedData
from src.fixtures.parameter_definitions import CLAUDE_45_BASE

CLAUDE_HAIKU_FAMILIES: list[ModelFamilySeedData] = [
    {
        "name": "Claude 4.5 Haiku",
        "family_identifier": "anthropic/claude-haiku-4.5",
        "description": "Anthropic Claude 4.5 Haiku. Fast, low-cost tier for RP.",
        "provider_types": ["anthropic", "openrouter", "opencode"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 4096, "min_value": 1, "max_value": 16384},
            **CLAUDE_45_BASE,
        },
        "unsupported_parameters": [],
        "extra_metadata": {
            "lineage": "claude-haiku",
            "context_window": 500000,
            "supports_vision": True,
            "supports_function_calling": True,
            "models": ["claude-4.5-haiku"],
        },
    },
]
