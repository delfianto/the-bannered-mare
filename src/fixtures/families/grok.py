"""xAI Grok model family seed data (base-model-generation keyed).

Grouped by generation. Grok 4.2 (xAI's official "4.20") is reasoning-only — no
stop/penalties — with a multi-agent variant that scales parallel agents via
reasoning_effort (low/medium = 4, high/xhigh = 16) plus an agent_count knob and
web_search/x_search. Grok 4.3 is the hybrid workhorse (1M context) supporting
stop, frequency/presence penalties, and reasoning_effort (none/low/medium); it
is the consolidated target the retired grok-4-fast / 4.1 / 4.1-fast redirect to.
Served via xAI or OpenRouter.

Grok 4.0 (256K) is omitted — it is sunsetting and delisted from OpenRouter.

Parameters per the xAI docs (docs.x.ai/developers/models).
"""

from src.fixtures.model_families import ModelFamilySeedData
from src.fixtures.parameter_definitions import (
    FREQUENCY_PENALTY,
    PRESENCE_PENALTY,
    STOP_LIST,
    XAI_BASE,
)

GROK_FAMILIES: list[ModelFamilySeedData] = [
    {
        "name": "Grok 4.2",
        "family_identifier": "xai/grok-4.2",
        "description": (
            "xAI Grok 4.20 (named 4.2 here) — flagship + multi-agent variant. 2M context, "
            "always-on reasoning (no stop/penalties). The multi-agent variant scales parallel "
            "agents via reasoning_effort (low/medium = 4, high/xhigh = 16) and agent_count, "
            "with web_search/x_search. Served via xAI or OpenRouter."
        ),
        "provider_types": ["xai", "openrouter"],
        "parameters": {
            "max_completion_tokens": {
                "type": "int",
                "default": 4096,
                "min_value": 1,
                "max_value": 2000000,
            },
            **XAI_BASE,
            # Multi-agent variant only: scales the number of parallel agents.
            "reasoning_effort": {
                "type": "enum",
                "default": "high",
                "str_values": ["low", "medium", "high", "xhigh"],
            },
            "agent_count": {"type": "int", "min_value": 1, "max_value": 16},
        },
        "unsupported_parameters": ["stop", "frequency_penalty", "presence_penalty"],
        "extra_metadata": {
            "lineage": "grok",
            "developer": "xai",
            "context_window": 2000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "note": (
                "official name Grok 4.20; multi-agent variant orchestrates parallel agents "
                "(web_search/x_search), up to 2M output"
            ),
            "models": ["grok-4.20", "grok-4.20-multi-agent"],
        },
    },
    {
        "name": "Grok 4.3",
        "family_identifier": "xai/grok-4.3",
        "description": (
            "xAI Grok 4.3. 1M context, hybrid reasoning via reasoning_effort (none/low/medium); "
            "supports stop and frequency/presence penalties. Consolidated target for the retired "
            "grok-4-fast / 4.1 / 4.1-fast. Served via xAI or OpenRouter."
        ),
        "provider_types": ["xai", "openrouter"],
        "parameters": {
            "max_completion_tokens": {
                "type": "int",
                "default": 4096,
                "min_value": 1,
                "max_value": 131072,
            },
            **XAI_BASE,
            "frequency_penalty": FREQUENCY_PENALTY,
            "presence_penalty": PRESENCE_PENALTY,
            "stop": STOP_LIST,
            "reasoning_effort": {
                "type": "enum",
                "default": "low",
                "str_values": ["none", "low", "medium"],
            },
        },
        "unsupported_parameters": [],
        "extra_metadata": {
            "lineage": "grok",
            "developer": "xai",
            "context_window": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "models": ["grok-4.3"],
        },
    },
]
