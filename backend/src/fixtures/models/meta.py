"""Current Meta models on OpenRouter; opt-in general-purpose catalog extras.

Older Muse Spark 1.1/1.2 remain discoverable but are superseded by 1.3. Wonder
Full is Muse Code-only; image, speech and safety classifiers are not chat seeds.
"""

from src.fixtures.models._types import ModelSeedData

OPENROUTER_META_MODELS: list[ModelSeedData] = [
    {
        "name": "Meta Muse Wonder",
        "model_identifier": "meta/muse-wonder",
        "family_identifier": "meta/muse-wonder",
        "provider_type": "openrouter",
        "parameters": {
            "max_tokens": 8192,
            "temperature": 1.0,
            "top_p": 1.0,
            "reasoning_effort": "medium",
        },
        "enabled": False,
    },
    {
        "name": "Meta Muse Spark 1.3",
        "model_identifier": "meta/muse-spark-1.3",
        "family_identifier": "meta/muse-spark-1.3",
        "provider_type": "openrouter",
        "parameters": {
            "max_tokens": 8192,
            "temperature": 1.0,
            "top_p": 1.0,
            "reasoning_effort": "medium",
        },
        "enabled": False,
    },
    {
        "name": "Meta Muse Spark 1.3 Contributor (training opt-in)",
        "model_identifier": "meta/muse-spark-1.3-contributor",
        "family_identifier": "meta/muse-spark-1.3-contributor",
        "provider_type": "openrouter",
        "parameters": {
            "max_tokens": 8192,
            "temperature": 1.0,
            "top_p": 1.0,
            "reasoning_effort": "medium",
        },
        "enabled": False,
    },
    {
        "name": "Meta Muse Spark Open",
        "model_identifier": "meta/muse-spark-open",
        "family_identifier": "meta/muse-spark-open",
        "provider_type": "openrouter",
        "parameters": {
            "max_tokens": 8192,
            "temperature": 1.0,
            "top_p": 1.0,
            "reasoning_effort": "medium",
        },
        "enabled": False,
    },
    {
        "name": "Meta Muse Glimmer 30B",
        "model_identifier": "meta/muse-glimmer-30b",
        "family_identifier": "meta/muse-glimmer",
        "provider_type": "openrouter",
        "parameters": {
            "max_tokens": 8192,
            "temperature": 1.0,
            "top_p": 1.0,
            "reasoning_effort": "medium",
        },
        "enabled": False,
    },
    {
        "name": "Meta Llama 4 Scout",
        "model_identifier": "meta-llama/llama-4-scout",
        "family_identifier": "meta/llama-4-scout",
        "provider_type": "openrouter",
        "parameters": {"max_tokens": 4096, "temperature": 1.0, "top_p": 0.95},
        "enabled": False,
    },
    {
        "name": "Meta Llama 4 Maverick",
        "model_identifier": "meta-llama/llama-4-maverick",
        "family_identifier": "meta/llama-4-maverick",
        "provider_type": "openrouter",
        "parameters": {"max_tokens": 4096, "temperature": 1.0, "top_p": 0.95},
        "enabled": False,
    },
    {
        "name": "Meta Llama 3.3 70B Instruct",
        "model_identifier": "meta-llama/llama-3.3-70b-instruct",
        "family_identifier": "meta/llama-3.3-instruct",
        "provider_type": "openrouter",
        "parameters": {"max_tokens": 4096, "temperature": 1.0, "top_p": 0.95},
        "enabled": False,
    },
]
