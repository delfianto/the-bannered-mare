"""Anthropic model family seed data."""

from src.fixtures.model_families import ModelFamilySeedData
from src.fixtures.parameter_definitions import STREAM, TEMPERATURE, TOP_K, TOP_P

_CLAUDE_BASE: dict = {
    "temperature": TEMPERATURE,
    "top_p": TOP_P,
    "top_k": TOP_K,
    "stop_sequences": {"type": "list", "item_schema": {"type": "string"}},
    "stream": STREAM,
    "system": {"type": "string"},
    "thinking": {
        "type": "object",
        "properties": {
            "type": {"type": "enum", "str_values": ["enabled", "disabled"]},
            "budget_tokens": {"type": "int", "min_value": 1024, "max_value": 20000},
        },
    },
}

_CLAUDE_46_BASE: dict = {
    "temperature": TEMPERATURE,
    "top_p": TOP_P,
    "top_k": TOP_K,
    "stop_sequences": {"type": "list", "item_schema": {"type": "string"}},
    "stream": STREAM,
    "system": {"type": "string"},
    "thinking": {
        "type": "object",
        "properties": {
            "type": {"type": "enum", "str_values": ["enabled", "disabled"]},
        },
    },
}

ANTHROPIC_FAMILIES: list[ModelFamilySeedData] = [
    {
        "name": "Claude 4.5 Standard",
        "family_identifier": "anthropic/claude-4.5-standard",
        "description": "Anthropic Claude 4.5 Haiku & Sonnet. Balanced speed/intelligence for RP.",
        "provider_types": ["anthropic", "openrouter"],
        "parameters": {
            "max_tokens": {
                "type": "int",
                "default": 4096,
                "min_value": 1,
                "max_value": 16384,
            },
            **_CLAUDE_BASE,
        },
        "unsupported_parameters": [],
        "extra_metadata": {
            "context_window": 500000,
            "supports_vision": True,
            "supports_function_calling": True,
            "models": ["claude-4.5-haiku", "claude-4.5-sonnet"],
        },
    },
    {
        "name": "Claude 4.5 Opus",
        "family_identifier": "anthropic/claude-4.5-opus",
        "description": "Anthropic Claude 4.5 Opus. High-cost, high-fidelity model.",
        "provider_types": ["anthropic", "openrouter"],
        "parameters": {
            "max_tokens": {
                "type": "int",
                "default": 4096,
                "min_value": 1,
                "max_value": 32768,
            },
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "top_k": {**TOP_K, "max_value": 500},
            "stop_sequences": {"type": "list", "item_schema": {"type": "string"}},
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
            "context_window": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "models": ["claude-4.5-opus"],
        },
    },
    {
        "name": "Claude 4.6 Sonnet",
        "family_identifier": "anthropic/claude-4.6-sonnet",
        "description": "Anthropic Claude 4.6 Sonnet. Fast, high-intelligence with adaptive thinking.",
        "provider_types": ["anthropic", "openrouter"],
        "parameters": {
            "max_tokens": {
                "type": "int",
                "default": 8192,
                "min_value": 1,
                "max_value": 64000,
            },
            "effort": {
                "type": "enum",
                "default": "high",
                "str_values": ["low", "medium", "high"],
            },
            **_CLAUDE_46_BASE,
        },
        "unsupported_parameters": [],
        "extra_metadata": {
            "context_window": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "models": ["claude-4.6-sonnet"],
        },
    },
    {
        "name": "Claude 4.6 Opus",
        "family_identifier": "anthropic/claude-4.6-opus",
        "description": "Anthropic Claude 4.6 Opus. Highest intelligence, adaptive thinking with fast mode.",
        "provider_types": ["anthropic", "openrouter"],
        "parameters": {
            "max_tokens": {
                "type": "int",
                "default": 8192,
                "min_value": 1,
                "max_value": 128000,
            },
            "effort": {
                "type": "enum",
                "default": "high",
                "str_values": ["low", "medium", "high", "max"],
            },
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "top_k": {**TOP_K, "max_value": 500},
            "stop_sequences": {"type": "list", "item_schema": {"type": "string"}},
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
            "context_window": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "models": ["claude-4.6-opus"],
        },
    },
]
