"""Google Gemini model seed data."""

from src.fixtures.models._types import ModelSeedData

_SAFETY_BLOCK_NONE = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

_GEMINI_BASE_PARAMS = {
    "max_output_tokens": 8192,
    "temperature": 0.85,
    "top_p": 0.9,
    "top_k": 60,
    "frequency_penalty": 0.3,
    "presence_penalty": 0.2,
    "safety_settings": _SAFETY_BLOCK_NONE,
}

GOOGLE_MODELS: list[ModelSeedData] = [
    {
        "name": "Gemini 2.5 Flash",
        "model_identifier": "gemini-2.5-flash",
        "openrouter_identifier": "google/gemini-2.5-flash",
        "family_identifier": "google/gemini-2.5",
        "provider_type": "google",
        "parameters": {**_GEMINI_BASE_PARAMS},
        "enabled": True,
        "use_openrouter": False,
    },
    {
        "name": "Gemini 2.5 Pro",
        "model_identifier": "gemini-2.5-pro",
        "openrouter_identifier": "google/gemini-2.5-pro",
        "family_identifier": "google/gemini-2.5",
        "provider_type": "google",
        "parameters": {**_GEMINI_BASE_PARAMS},
        "enabled": True,
        "use_openrouter": False,
    },
    {
        "name": "Gemini 3 Flash (Preview)",
        "model_identifier": "gemini-3-flash-preview",
        "openrouter_identifier": "google/gemini-3-flash-preview",
        "family_identifier": "google/gemini-3-preview",
        "provider_type": "google",
        "parameters": {**_GEMINI_BASE_PARAMS, "thinking_level": "minimal"},
        "enabled": True,
        "use_openrouter": False,
    },
    {
        "name": "Gemini 3.1 Pro (Preview)",
        "model_identifier": "gemini-3.1-pro-preview",
        "openrouter_identifier": "google/gemini-3.1-pro-preview",
        "family_identifier": "google/gemini-3-preview",
        "provider_type": "google",
        "parameters": {**_GEMINI_BASE_PARAMS, "thinking_level": "minimal"},
        "enabled": True,
        "use_openrouter": False,
    },
]
