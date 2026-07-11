"""OpenAI model seed data."""

from src.fixtures.models._types import ModelSeedData

# Chat models: classic sampling.
_CHAT_PARAMS = {
    "max_completion_tokens": 4096,
    "temperature": 0.85,
    "top_p": 0.9,
    "frequency_penalty": 0.3,
    "presence_penalty": 0.2,
}

# Reasoning models: no sampling; reasoning_effort + verbosity + reasoning summary.
_THINKING_PARAMS = {
    "max_completion_tokens": 16384,
    "reasoning_effort": "low",
    "verbosity": "low",
    "summary": "concise",
}

OPENAI_MODELS: list[ModelSeedData] = [
    # --- GPT-4o (chat) ---
    {
        "name": "GPT-4o",
        "model_identifier": "gpt-4o",
        "family_identifier": "openai/gpt-4o",
        "provider_type": "openai",
        "parameters": {**_CHAT_PARAMS},
        "enabled": False,
    },
    {
        "name": "GPT-4o Mini",
        "model_identifier": "gpt-4o-mini",
        "family_identifier": "openai/gpt-4o",
        "provider_type": "openai",
        "parameters": {**_CHAT_PARAMS, "max_completion_tokens": 16384},
        "enabled": False,
    },
    # --- GPT-4.1 (chat) ---
    {
        "name": "GPT-4.1",
        "model_identifier": "gpt-4.1",
        "family_identifier": "openai/gpt-4.1",
        "provider_type": "openai",
        "parameters": {**_CHAT_PARAMS},
        "enabled": False,
    },
    {
        "name": "GPT-4.1 Mini",
        "model_identifier": "gpt-4.1-mini",
        "family_identifier": "openai/gpt-4.1",
        "provider_type": "openai",
        "parameters": {**_CHAT_PARAMS},
        "enabled": False,
    },
    {
        "name": "GPT-4.1 Nano",
        "model_identifier": "gpt-4.1-nano",
        "family_identifier": "openai/gpt-4.1",
        "provider_type": "openai",
        "parameters": {**_CHAT_PARAMS},
        "enabled": False,
    },
    # --- GPT-5 chat (non-reasoning) ---
    # OpenAI's chat SKUs are only callable via the "-chat-latest" rolling alias
    # (there is no bare "gpt-5-chat" on the API), so the native route uses that
    # id. The canonical slug is pinned to the clean "gpt-5.x-chat" so it folds
    # with the OpenRouter route "openai/gpt-5.x-chat".
    {
        "name": "GPT-5 Chat",
        "model_identifier": "gpt-5-chat-latest",
        "slug": "gpt-5-chat",
        "family_identifier": "openai/gpt-5-chat",
        "provider_type": "openai",
        "parameters": {**_CHAT_PARAMS, "max_completion_tokens": 8192},
        "enabled": False,
    },
    {
        "name": "GPT-5.1 Chat",
        "model_identifier": "gpt-5.1-chat-latest",
        "slug": "gpt-5.1-chat",
        "family_identifier": "openai/gpt-5-chat",
        "provider_type": "openai",
        "parameters": {**_CHAT_PARAMS, "max_completion_tokens": 8192},
        "enabled": False,
    },
    {
        "name": "GPT-5.2 Chat",
        "model_identifier": "gpt-5.2-chat-latest",
        "slug": "gpt-5.2-chat",
        "family_identifier": "openai/gpt-5-chat",
        "provider_type": "openai",
        "parameters": {**_CHAT_PARAMS, "max_completion_tokens": 8192},
        "enabled": False,
    },
    {
        "name": "GPT-5.3 Chat",
        "model_identifier": "gpt-5.3-chat-latest",
        "slug": "gpt-5.3-chat",
        "family_identifier": "openai/gpt-5-chat",
        "provider_type": "openai",
        "parameters": {**_CHAT_PARAMS, "max_completion_tokens": 8192},
        "enabled": False,
    },
    # --- GPT-5 thinking (reasoning) ---
    # "-latest" rolling aliases and dated snapshots (gpt-5.4-2026-03-05, …) are
    # intentionally omitted: they duplicate a bare SKU and are filtered out of
    # provider discovery too (see ProviderService._filter_blacklisted).
    {
        "name": "GPT-5.4 Pro",
        "model_identifier": "gpt-5.4-pro",
        "family_identifier": "openai/gpt-5-thinking",
        "provider_type": "openai",
        "parameters": {**_THINKING_PARAMS, "reasoning_effort": "high"},
        "enabled": False,
    },
    {
        "name": "GPT-5.5",
        "model_identifier": "gpt-5.5",
        "family_identifier": "openai/gpt-5-thinking",
        "provider_type": "openai",
        "parameters": {**_THINKING_PARAMS},
        "enabled": False,
    },
    {
        "name": "GPT-5.5 Pro",
        "model_identifier": "gpt-5.5-pro",
        "family_identifier": "openai/gpt-5-thinking",
        "provider_type": "openai",
        "parameters": {**_THINKING_PARAMS, "reasoning_effort": "high"},
        "enabled": False,
    },
    # --- GPT-5.6 (reasoning; Sol / Terra / Luna) ---
    {
        "name": "GPT-5.6 Sol",
        "model_identifier": "gpt-5.6-sol",
        "family_identifier": "openai/gpt-5.6",
        "provider_type": "openai",
        "parameters": {**_THINKING_PARAMS, "reasoning_effort": "medium"},
        "enabled": False,
    },
    {
        "name": "GPT-5.6 Terra",
        "model_identifier": "gpt-5.6-terra",
        "family_identifier": "openai/gpt-5.6",
        "provider_type": "openai",
        "parameters": {**_THINKING_PARAMS},
        "enabled": False,
    },
    {
        "name": "GPT-5.6 Luna",
        "model_identifier": "gpt-5.6-luna",
        "family_identifier": "openai/gpt-5.6",
        "provider_type": "openai",
        "parameters": {**_THINKING_PARAMS, "max_completion_tokens": 8192},
        "enabled": False,
    },
]
