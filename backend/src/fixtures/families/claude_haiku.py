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
            "reasoning_mode": "optional",
            "lineage": "claude-haiku",
            "context_window": 500000,
            "supports_vision": True,
            "supports_function_calling": True,
            "supports_prompt_caching": True,
            "models": ["claude-4.5-haiku"],
        },
    },
    # Catalog refresh: 2026-10-23; https://platform.claude.com/docs/en/build-with-claude/effort
    {
        "name": "Claude Haiku 5.5",
        "family_identifier": "anthropic/claude-haiku-5.5",
        "description": "Claude Haiku 5.5. 1M context, 128K output. Adaptive thinking; sampling parameters "
        "removed.",
        "provider_types": ["anthropic", "openrouter"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 8192, "min_value": 1, "max_value": 128000},
            "effort": {
                "type": "enum",
                "default": "medium",
                "str_values": ["low", "medium", "high", "xhigh", "max"],
            },
            "stop_sequences": {"type": "list", "item_schema": {"type": "string"}},
            "stream": {"type": "boolean", "default": True},
            "system": {"type": "string"},
            "thinking": {
                "type": "object",
                "properties": {"type": {"type": "enum", "str_values": ["adaptive", "disabled"]}},
            },
        },
        "unsupported_parameters": ["temperature", "top_p", "top_k", "budget_tokens"],
        "extra_metadata": {
            "reasoning_mode": "optional",
            "lineage": "claude-haiku",
            "context_window": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "supports_prompt_caching": True,
            "models": ["claude-haiku-5-5", "anthropic/claude-haiku-5.5"],
        },
    },
]
