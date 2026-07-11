"""xAI Grok model family seed data (base-model-generation keyed).

Grouped by generation. Grok 4.2 (xAI's official "4.20") is reasoning-only — no
stop/penalties — with a multi-agent variant that scales parallel agents via
reasoning_effort (low/medium = 4, high/xhigh = 16) plus an agent_count knob and
web_search/x_search. Grok 4.3 is the hybrid workhorse (1M context) with
reasoning_effort (none/low/medium); it is the consolidated target the retired
grok-4-fast / 4.1 / 4.1-fast redirect to. Grok 4.5 is the latest reasoning model
(500K context, reasoning_effort low/medium/high, default high) built for coding,
agentic, and knowledge work, with native web/X search and code execution. Served
via xAI or OpenRouter.

All three are reasoning models, and xAI reasoning models reject stop and the
frequency/presence penalties (a 400) — so each lists those in
unsupported_parameters. Grok 4.3 can turn reasoning off with
reasoning_effort="none", on which path xAI accepts them again, but the family
default is reasoning-on and the schema can't express that conditional, so we mark
them unsupported to keep the default request safe.

Grok 4.0 (256K) is omitted — it is sunsetting and delisted from OpenRouter.

Parameters per the xAI docs (docs.x.ai/developers/models).
"""

from src.fixtures.model_families import ModelFamilySeedData
from src.fixtures.parameter_definitions import OPENAI_REJECTED_SAMPLERS, XAI_BASE

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
        "unsupported_parameters": [
            "stop",
            "frequency_penalty",
            "presence_penalty",
            *OPENAI_REJECTED_SAMPLERS,
        ],
        "extra_metadata": {
            "lineage": "grok",
            "developer": "xai",
            "context_window": 2000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "note": "official name Grok 4.20; up to 2M output",
            "models": ["grok-4.20"],
        },
    },
    {
        "name": "Grok 4.3",
        "family_identifier": "xai/grok-4.3",
        "description": (
            "xAI Grok 4.3. 1M context, hybrid reasoning via reasoning_effort (none/low/medium). "
            "As a reasoning model it rejects stop and frequency/presence penalties (except on the "
            "reasoning_effort=none path). Consolidated target for the retired grok-4-fast / 4.1 / "
            "4.1-fast. Served via xAI or OpenRouter."
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
            "reasoning_effort": {
                "type": "enum",
                "default": "low",
                "str_values": ["none", "low", "medium"],
            },
        },
        "unsupported_parameters": [
            "stop",
            "frequency_penalty",
            "presence_penalty",
            *OPENAI_REJECTED_SAMPLERS,
        ],
        "extra_metadata": {
            "lineage": "grok",
            "developer": "xai",
            "context_window": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "models": ["grok-4.3"],
        },
    },
    {
        "name": "Grok 4.5",
        "family_identifier": "xai/grok-4.5",
        "description": (
            "xAI Grok 4.5 — reasoning model for coding, agentic, and knowledge work. 500K "
            "context, up to 30K output, reasoning_effort (low/medium/high, default high), and "
            "native tool calling (web/X search, code execution). As a reasoning model it rejects "
            "stop and the frequency/presence penalties. Served via xAI, OpenRouter, or OpenCode Zen."
        ),
        "provider_types": ["xai", "openrouter", "opencode"],
        "parameters": {
            "max_completion_tokens": {
                "type": "int",
                "default": 4096,
                "min_value": 1,
                "max_value": 30000,
            },
            **XAI_BASE,
            "reasoning_effort": {
                "type": "enum",
                "default": "high",
                "str_values": ["low", "medium", "high"],
            },
        },
        "unsupported_parameters": [
            "stop",
            "frequency_penalty",
            "presence_penalty",
            *OPENAI_REJECTED_SAMPLERS,
        ],
        "extra_metadata": {
            "lineage": "grok",
            "developer": "xai",
            "context_window": 500000,
            "supports_vision": True,
            "supports_function_calling": True,
            "note": "reasoning-only (low/medium/high, default high); native web/X search + code execution",
            "models": ["grok-4.5"],
        },
    },
]
