"""Ollama (local) model seed data — TheDrummer RP + Gemma 4."""

from src.fixtures.models._types import ModelSeedData

_DRUMMER_PARAMS = {
    "temperature": 0.9,
    "top_p": 0.92,
    "top_k": 65,
    "repeat_penalty": 1.1,
    "num_ctx": 8192,
}

_GEMMA4_PARAMS = {
    "temperature": 0.8,
    "top_p": 0.9,
    "top_k": 60,
    "num_ctx": 32768,
}

OLLAMA_MODELS: list[ModelSeedData] = [
    {
        "name": "Cydonia 24B v3.1 Q4_K_M",
        "model_identifier": "thedrummer/cydonia:24b-v3.1-q4_k_m",
        "openrouter_identifier": None,
        "family_identifier": "ollama/thedrummer-rp",
        "provider_type": "ollama",
        "parameters": {**_DRUMMER_PARAMS},
        "enabled": True,
    },
    {
        "name": "Skyfall 31B v4.2 Q4_K_M",
        "model_identifier": "thedrummer/skyfall:31b-v4.2-q4_k_m",
        "openrouter_identifier": None,
        "family_identifier": "ollama/thedrummer-rp",
        "provider_type": "ollama",
        "parameters": {**_DRUMMER_PARAMS},
        "enabled": True,
    },
    {
        "name": "Rocinante 12B v1.1 Q4_K_M",
        "model_identifier": "thedrummer/rocinante:12b-v1.1-q4_k_m",
        "openrouter_identifier": None,
        "family_identifier": "ollama/thedrummer-rp",
        "provider_type": "ollama",
        "parameters": {**_DRUMMER_PARAMS},
        "enabled": True,
    },
    {
        "name": "Gemma 4 4B Q4_K_M",
        "model_identifier": "gemma4:latest",
        "openrouter_identifier": None,
        "family_identifier": "ollama/gemma-4",
        "provider_type": "ollama",
        "parameters": {**_GEMMA4_PARAMS},
        "enabled": True,
    },
    {
        "name": "Gemma 4 12B Q4_K_M",
        "model_identifier": "gemma4:12b",
        "openrouter_identifier": None,
        "family_identifier": "ollama/gemma-4",
        "provider_type": "ollama",
        "parameters": {**_GEMMA4_PARAMS},
        "enabled": True,
    },
    {
        "name": "Gemma 4 27B Q4_K_M",
        "model_identifier": "gemma4:27b",
        "openrouter_identifier": None,
        "family_identifier": "ollama/gemma-4",
        "provider_type": "ollama",
        "parameters": {**_GEMMA4_PARAMS},
        "enabled": True,
    },
]
