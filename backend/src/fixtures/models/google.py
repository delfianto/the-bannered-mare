"""Google Gemini model seed data."""

from src.fixtures.models._types import ModelSeedData

_SAFETY_BLOCK_NONE = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# Gemini 2.5: full sampling surface (top_k + penalties).
_GEMINI_25_PARAMS = {
    "max_output_tokens": 8192,
    "temperature": 0.85,
    "top_p": 0.9,
    "top_k": 60,
    "frequency_penalty": 0.3,
    "presence_penalty": 0.2,
    "safety_settings": _SAFETY_BLOCK_NONE,
}

# Gemini 3.x dropped top_k and the penalties and replaced thinkingBudget with
# thinking_level; temperature defaults to 1.0 and is best left unset.
_GEMINI_3_PARAMS = {
    "max_output_tokens": 8192,
    "thinking_level": "low",
    "safety_settings": _SAFETY_BLOCK_NONE,
}

GOOGLE_MODELS: list[ModelSeedData] = [
    # --- Gemini 2.5 ---
    {
        "name": "Gemini 2.5 Pro",
        "model_identifier": "gemini-2.5-pro",
        "family_identifier": "google/gemini-2.5",
        "provider_type": "google",
        "parameters": {**_GEMINI_25_PARAMS},
        "enabled": False,
    },
    {
        "name": "Gemini 2.5 Flash",
        "model_identifier": "gemini-2.5-flash",
        "family_identifier": "google/gemini-2.5",
        "provider_type": "google",
        "parameters": {**_GEMINI_25_PARAMS},
        "enabled": False,
    },
    {
        "name": "Gemini 2.5 Flash-Lite",
        "model_identifier": "gemini-2.5-flash-lite",
        "family_identifier": "google/gemini-2.5",
        "provider_type": "google",
        "parameters": {**_GEMINI_25_PARAMS},
        "enabled": False,
    },
    # --- Gemini 3.x ---
    {
        "name": "Gemini 3 Flash (Preview)",
        "model_identifier": "gemini-3-flash-preview",
        "family_identifier": "google/gemini-3",
        "provider_type": "google",
        "parameters": {**_GEMINI_3_PARAMS},
        "enabled": False,
    },
    {
        "name": "Gemini 3.1 Pro (Preview)",
        "model_identifier": "gemini-3.1-pro-preview",
        "family_identifier": "google/gemini-3",
        "provider_type": "google",
        "parameters": {**_GEMINI_3_PARAMS},
        "enabled": False,
    },
    {
        "name": "Gemini 3.1 Flash-Lite",
        "model_identifier": "gemini-3.1-flash-lite",
        "family_identifier": "google/gemini-3",
        "provider_type": "google",
        "parameters": {**_GEMINI_3_PARAMS},
        "enabled": False,
    },
    # --- Gemini 3.5 ---
    {
        "name": "Gemini 3.5 Flash",
        "model_identifier": "gemini-3.5-flash",
        "family_identifier": "google/gemini-3.5",
        "provider_type": "google",
        # 3.5 shares the no-sampling shape; thinking_level "low" is valid (it also adds "minimal").
        "parameters": {**_GEMINI_3_PARAMS},
        "enabled": False,
    },
]
