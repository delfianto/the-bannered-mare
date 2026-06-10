"""xAI Grok model seed data."""

from src.fixtures.models._types import ModelSeedData

XAI_MODELS: list[ModelSeedData] = [
    # --- Grok 4.2 (official name 4.20) ---
    {
        "name": "Grok 4.20",
        "model_identifier": "grok-4.20",
        "openrouter_identifier": "x-ai/grok-4.20",
        "family_identifier": "grok-4.2",
        "provider_type": "xai",
        "parameters": {
            "max_completion_tokens": 4096,
            "temperature": 0.9,
            "top_p": 0.92,
        },
        "enabled": True,
        "use_openrouter": False,
    },
    {
        "name": "Grok 4.20 Multi-Agent",
        "model_identifier": "grok-4.20-multi-agent",
        "openrouter_identifier": "x-ai/grok-4.20-multi-agent",
        "family_identifier": "grok-4.2",
        "provider_type": "xai",
        # Multi-agent thinking preserves narrative/instructions well for RP;
        # reasoning_effort scales the parallel-agent count (high = 16).
        "parameters": {
            "max_completion_tokens": 4096,
            "temperature": 0.9,
            "top_p": 0.92,
            "reasoning_effort": "high",
        },
        "enabled": True,
        "use_openrouter": False,
    },
    # --- Grok 4.3 ---
    {
        "name": "Grok 4.3",
        "model_identifier": "grok-4.3",
        "openrouter_identifier": "x-ai/grok-4.3",
        "family_identifier": "grok-4.3",
        "provider_type": "xai",
        "parameters": {
            "max_completion_tokens": 4096,
            "temperature": 0.9,
            "top_p": 0.92,
            "reasoning_effort": "low",
        },
        "enabled": True,
        "use_openrouter": False,
    },
]
