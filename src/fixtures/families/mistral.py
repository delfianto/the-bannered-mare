"""Mistral base-model family seed data (provider-agnostic, base-model keyed).

Open-weight Mistral models and their finetunes are grouped by the *actual base
model* they sit on, not by finetune author. They share one sampling contract
but split on the base architecture line (12B Nemo vs 24B Small). Finetune author
and the exact per-model base model live in ``extra_metadata`` (the ``Model`` row
has no metadata column). All run as local GGUF (Ollama) or hosted (OpenRouter).

Base models verified against the HuggingFace model cards.
"""

from src.fixtures.model_families import ModelFamilySeedData

# Shared sampling contract for Mistral-based RP models (llama.cpp / Ollama style,
# plus a hosted output cap). Defaults lean RP. Bare dict to mirror the codebase's
# shared-block style.
_MISTRAL_RP_PARAMS: dict = {
    "temperature": {"type": "float", "default": 0.9, "min_value": 0.0, "max_value": 2.0},
    "top_p": {"type": "float", "default": 0.92, "min_value": 0.0, "max_value": 1.0},
    "top_k": {"type": "int", "default": 65, "min_value": 1, "max_value": 200},
    "repeat_penalty": {"type": "float", "default": 1.1, "min_value": 1.0, "max_value": 2.0},
    "num_ctx": {"type": "int", "default": 8192, "min_value": 512, "max_value": 131072},
    "max_tokens": {"type": "int", "default": 4096, "min_value": 1, "max_value": 16384},
}

MISTRAL_FAMILIES: list[ModelFamilySeedData] = [
    {
        "name": "Mistral Nemo 12B",
        "family_identifier": "mistral-nemo",
        "description": (
            "Mistral Nemo 12B base and its finetunes (e.g. TheDrummer's Rocinante). "
            "Text-only, ~128K context. Local (Ollama GGUF) or hosted (OpenRouter)."
        ),
        "provider_types": ["ollama", "openrouter"],
        "parameters": {**_MISTRAL_RP_PARAMS},
        "unsupported_parameters": [],
        "extra_metadata": {
            "lineage": "mistral",
            "base_family": "Mistral Nemo 12B",
            "base_model": "mistralai/Mistral-Nemo-Base-2407",
            "context_window": 131072,
            "supports_vision": False,
            "supports_function_calling": False,
            "quantization": "Q4_K_M",
            # Exact base model per finetune (Model rows carry no metadata column).
            # Rocinante's HF card has no base_model field; lineage confirmed via
            # config (MistralForCausalLM, 12.2B) + "Mistral for NeMo" template.
            "finetunes": {
                "thedrummer/rocinante:12b-v1.1-q4_k_m": {
                    "author": "TheDrummer",
                    "base_model": "mistralai/Mistral-Nemo-Base-2407",
                },
            },
            "models": ["thedrummer/rocinante:12b-v1.1-q4_k_m"],
        },
    },
    {
        "name": "Mistral Small 24B",
        "family_identifier": "mistral-small",
        "description": (
            "Mistral Small 24B (3.1 / 3.2, including the Magistral reasoning variant) base "
            "and its finetunes (e.g. TheDrummer's Skyfall, Cydonia). 128K context. "
            "Local (Ollama GGUF) or hosted (OpenRouter)."
        ),
        "provider_types": ["ollama", "openrouter"],
        "parameters": {**_MISTRAL_RP_PARAMS},
        "unsupported_parameters": [],
        "extra_metadata": {
            "lineage": "mistral",
            "base_family": "Mistral Small 24B (3.1 / 3.2, incl. Magistral)",
            "base_models": [
                "mistralai/Mistral-Small-3.2-24B-Instruct-2507",
                "mistralai/Magistral-Small-2506",
                "mistralai/Mistral-Small-3.1-24B-Instruct-2503",
            ],
            "context_window": 131072,
            "supports_vision": False,
            "supports_function_calling": False,
            "quantization": "Q4_K_M",
            "finetunes": {
                "thedrummer/skyfall:31b-v4.2-q4_k_m": {
                    "author": "TheDrummer",
                    "base_model": "mistralai/Mistral-Small-3.2-24B-Instruct-2507",
                    "note": "upscaled to 31B",
                },
                "thedrummer/cydonia:24b-v3.1-q4_k_m": {
                    "author": "TheDrummer",
                    "base_model": "mistralai/Magistral-Small-2506",
                },
            },
            "models": [
                "thedrummer/skyfall:31b-v4.2-q4_k_m",
                "thedrummer/cydonia:24b-v3.1-q4_k_m",
            ],
        },
    },
]
