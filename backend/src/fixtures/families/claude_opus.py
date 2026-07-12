"""Claude Opus tier family seed data.

Opus is Anthropic's highest-capability tier. Each generation is its own record
because the parameter contract shifts: 4.5 uses an explicit thinking
`budget_tokens`; 4.6 moved to adaptive thinking plus an `effort` enum with a
"max" tier. Opus also allows `top_k` up to 500. Provider-agnostic — runs on the
Anthropic API or via OpenRouter.
"""

from src.fixtures.model_families import ModelFamilySeedData
from src.fixtures.parameter_definitions import (
    CLAUDE_47_BASE,
    CLAUDE_TEMPERATURE,
    CLAUDE_TOP_P,
    STOP_LIST,
    STREAM,
    TOP_K,
)

CLAUDE_OPUS_FAMILIES: list[ModelFamilySeedData] = [
    {
        "name": "Claude 4.5 Opus",
        "family_identifier": "anthropic/claude-opus-4.5",
        "description": "Anthropic Claude 4.5 Opus. High-cost, high-fidelity model.",
        "provider_types": ["anthropic", "openrouter", "opencode"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 4096, "min_value": 1, "max_value": 32768},
            "effort": {"type": "enum", "default": "high", "str_values": ["low", "medium", "high"]},
            "temperature": CLAUDE_TEMPERATURE,
            "top_p": CLAUDE_TOP_P,
            "top_k": {**TOP_K, "max_value": 500},
            "stop_sequences": STOP_LIST,
            "stream": STREAM,
            "system": {"type": "string"},
            "thinking": {
                "type": "object",
                "properties": {
                    "type": {"type": "enum", "str_values": ["enabled", "disabled"]},
                    "budget_tokens": {"type": "int", "min_value": 1024, "max_value": 32000},
                },
            },
            "metadata": {"type": "object"},
        },
        "unsupported_parameters": [],
        "extra_metadata": {
            "reasoning_mode": "optional",
            "lineage": "claude-opus",
            "context_window": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "models": ["claude-4.5-opus"],
        },
    },
    {
        "name": "Claude 4.6 Opus",
        "family_identifier": "anthropic/claude-opus-4.6",
        "description": "Anthropic Claude 4.6 Opus. Highest intelligence, adaptive thinking with fast mode.",
        "provider_types": ["anthropic", "openrouter", "opencode"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 8192, "min_value": 1, "max_value": 128000},
            "effort": {
                "type": "enum",
                "default": "high",
                "str_values": ["low", "medium", "high", "max"],
            },
            "temperature": CLAUDE_TEMPERATURE,
            "top_p": CLAUDE_TOP_P,
            "top_k": {**TOP_K, "max_value": 500},
            "stop_sequences": STOP_LIST,
            "stream": STREAM,
            "system": {"type": "string"},
            "thinking": {
                "type": "object",
                "properties": {
                    "type": {"type": "enum", "str_values": ["enabled", "disabled"]},
                },
            },
            "metadata": {"type": "object"},
        },
        "unsupported_parameters": [],
        "extra_metadata": {
            "reasoning_mode": "optional",
            "lineage": "claude-opus",
            "context_window": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "models": ["claude-4.6-opus"],
        },
    },
    {
        "name": "Claude 4.7 Opus",
        "family_identifier": "anthropic/claude-opus-4.7",
        "description": (
            "Anthropic Claude 4.7 Opus. Highly autonomous, long-horizon agentic work. "
            "Adaptive thinking only; sampling parameters (temperature/top_p/top_k) removed."
        ),
        "provider_types": ["anthropic", "openrouter", "opencode"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 8192, "min_value": 1, "max_value": 128000},
            "effort": {
                "type": "enum",
                "default": "high",
                "str_values": ["low", "medium", "high", "xhigh", "max"],
            },
            **CLAUDE_47_BASE,
            "metadata": {"type": "object"},
        },
        "unsupported_parameters": ["temperature", "top_p", "top_k", "budget_tokens"],
        "extra_metadata": {
            "reasoning_mode": "optional",
            "lineage": "claude-opus",
            "context_window": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "models": ["claude-4.7-opus"],
        },
    },
    {
        "name": "Claude 4.8 Opus",
        "family_identifier": "anthropic/claude-opus-4.8",
        "description": (
            "Anthropic Claude 4.8 Opus. Most capable Opus tier; state-of-the-art long-horizon "
            "agentic work. Same surface as 4.7 — adaptive thinking only, no sampling parameters."
        ),
        "provider_types": ["anthropic", "openrouter", "opencode"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 8192, "min_value": 1, "max_value": 128000},
            "effort": {
                "type": "enum",
                "default": "high",
                "str_values": ["low", "medium", "high", "xhigh", "max"],
            },
            **CLAUDE_47_BASE,
            "metadata": {"type": "object"},
        },
        "unsupported_parameters": ["temperature", "top_p", "top_k", "budget_tokens"],
        "extra_metadata": {
            "reasoning_mode": "optional",
            "lineage": "claude-opus",
            "context_window": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "models": ["claude-4.8-opus"],
        },
    },
]
