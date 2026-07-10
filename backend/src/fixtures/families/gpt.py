"""OpenAI GPT model family seed data (base-model-generation keyed).

Grouped by generation and the hard chat-vs-reasoning contract split. The chat
families (gpt-4o, gpt-4.1, gpt-5-chat) use classic sampling (temperature, top_p,
penalties). The reasoning family (gpt-5-thinking) rejects every sampling param
(400) and instead exposes reasoning_effort + verbosity (+ a reasoning summary);
it consolidates every 5.x reasoning model (5.4, 5.5, incl. mini/nano/pro).
Image and codex variants are omitted (not chat/RP). Served via OpenAI or
OpenRouter.

Parameters per the OpenAI API docs (developers.openai.com).
"""

from src.fixtures.model_families import ModelFamilySeedData
from src.fixtures.parameter_definitions import (
    OPENAI_REJECTED_SAMPLERS,
    OPENAI_SAMPLING,
    OPENAI_THINKING_COMMON,
)

# top_k/min_p/top_a/repetition_penalty aren't OpenAI params — the API 400s on them.
_UNSUPPORTED_CHAT = [
    "max_tokens",
    "reasoning_effort",
    "summary",
    "verbosity",
    *OPENAI_REJECTED_SAMPLERS,
]
_UNSUPPORTED_THINKING = [
    "max_tokens",
    "temperature",
    "top_p",
    "frequency_penalty",
    "presence_penalty",
    "logprobs",
    "top_logprobs",
    "logit_bias",
    *OPENAI_REJECTED_SAMPLERS,
]

GPT_FAMILIES: list[ModelFamilySeedData] = [
    {
        "name": "OpenAI GPT-4o",
        "family_identifier": "openai/gpt-4o",
        "description": "OpenAI GPT-4o family (incl. mini). 128K context, multimodal, classic sampling.",
        "provider_types": ["openai", "openrouter", "opencode"],
        "parameters": {
            "max_completion_tokens": {
                "type": "int",
                "default": 4096,
                "min_value": 1,
                "max_value": 16384,
            },
            **OPENAI_SAMPLING,
        },
        "unsupported_parameters": _UNSUPPORTED_CHAT,
        "extra_metadata": {
            "lineage": "gpt",
            "developer": "openai",
            "context_window": 128000,
            "supports_vision": True,
            "supports_function_calling": True,
            "models": ["gpt-4o", "gpt-4o-mini"],
        },
    },
    {
        "name": "OpenAI GPT-4.1",
        "family_identifier": "openai/gpt-4.1",
        "description": "OpenAI GPT-4.1 family (incl. mini, nano). 1M context, classic sampling.",
        "provider_types": ["openai", "openrouter", "opencode"],
        "parameters": {
            "max_completion_tokens": {
                "type": "int",
                "default": 4096,
                "min_value": 1,
                "max_value": 32768,
            },
            **OPENAI_SAMPLING,
        },
        "unsupported_parameters": _UNSUPPORTED_CHAT,
        "extra_metadata": {
            "lineage": "gpt",
            "developer": "openai",
            "context_window": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            "models": ["gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano"],
        },
    },
    {
        "name": "OpenAI GPT-5 Chat",
        "family_identifier": "openai/gpt-5-chat",
        "description": (
            "OpenAI GPT-5 chat models (5, 5.1, 5.2, 5.3, chat-latest) — non-reasoning, "
            "classic sampling. Up to 400K context."
        ),
        "provider_types": ["openai", "openrouter", "opencode"],
        "parameters": {
            "max_completion_tokens": {
                "type": "int",
                "default": 8192,
                "min_value": 1,
                "max_value": 128000,
            },
            **OPENAI_SAMPLING,
        },
        "unsupported_parameters": _UNSUPPORTED_CHAT,
        "extra_metadata": {
            "lineage": "gpt",
            "developer": "openai",
            "context_window": 400000,
            "supports_vision": False,
            "supports_function_calling": True,
            "models": [
                "gpt-5-chat",
                "gpt-5.1-chat",
                "gpt-5.2-chat",
                "gpt-5.3-chat",
                "gpt-chat-latest",
            ],
        },
    },
    {
        "name": "OpenAI GPT-5 Thinking",
        "family_identifier": "openai/gpt-5-thinking",
        "description": (
            "OpenAI GPT-5.x reasoning models (5.4, 5.5, incl. mini/nano/pro). Extended "
            "reasoning via reasoning_effort + verbosity; sampling parameters are removed. "
            "Up to ~1M context."
        ),
        "provider_types": ["openai", "openrouter", "opencode"],
        "parameters": {
            "max_completion_tokens": {
                "type": "int",
                "default": 8192,
                "min_value": 1,
                "max_value": 128000,
            },
            "reasoning_effort": {
                "type": "enum",
                "default": "medium",
                "str_values": ["low", "medium", "high", "xhigh"],
            },
            "verbosity": {
                "type": "enum",
                "default": "medium",
                "str_values": ["low", "medium", "high"],
            },
            # Reasoning summary control (Responses API): summarizes the reasoning.
            "summary": {
                "type": "enum",
                "default": "auto",
                "str_values": ["concise", "detailed", "auto"],
            },
            **OPENAI_THINKING_COMMON,
        },
        "unsupported_parameters": _UNSUPPORTED_THINKING,
        "extra_metadata": {
            "lineage": "gpt",
            "developer": "openai",
            "context_window": 1000000,
            "supports_vision": True,
            "supports_function_calling": True,
            # reasoning_effort "xhigh" is GPT-5.5+; 5.4 caps at "high".
            "note": "reasoning_effort xhigh is GPT-5.5+ only; 5.4 caps at high",
            "models": [
                "gpt-5.4",
                "gpt-5.4-mini",
                "gpt-5.4-nano",
                "gpt-5.4-pro",
                "gpt-5.5",
                "gpt-5.5-pro",
            ],
        },
    },
]
