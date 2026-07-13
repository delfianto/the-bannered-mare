"""Gemma model family seed data (provider-agnostic base lineage).

Google Gemma is an open-weight base family served identically as local GGUF
(Ollama) and hosted (OpenRouter), so a single family record spans both
providers. ``num_ctx`` is the local context control; ``max_tokens`` caps hosted
output. This replaces the former provider-split ``ollama/gemma-4`` +
``openrouter/gemma`` duplicates.
"""

from src.fixtures.model_families import ModelFamilySeedData
from src.fixtures.parameter_definitions import MIN_P, TEMPERATURE, TOP_K, TOP_P_95

GEMMA_FAMILIES: list[ModelFamilySeedData] = [
    {
        "name": "Gemma 4",
        "family_identifier": "google/gemma-4",
        "description": (
            "Google Gemma 4 open-weight family (E2B, E4B, 12B, 26B A4B MoE, 31B). "
            "Multimodal, up to 256K context, thinking mode. Runs locally (Ollama GGUF) "
            "or hosted (OpenRouter)."
        ),
        "provider_types": ["ollama", "lmstudio", "openrouter"],
        "parameters": {
            # Official Gemma 4 sampling guidance: temperature=1.0, top_p=0.95, top_k=64
            "temperature": TEMPERATURE,
            "top_p": TOP_P_95,
            "top_k": {**TOP_K, "default": 64, "max_value": 200},
            # RP-community tail cutoff; pairs with a hotter temperature. 0 = off.
            "min_p": MIN_P,
            # Gemma 4 thinking. Native control is a boolean (<|think|> token /
            # enable_thinking, default off), but the graded surfaces expose a level:
            # Gemini API thinking_level, Bedrock reasoning_effort, OpenRouter
            # reasoning.effort. We model it as a level (minimal = effectively off).
            "thinking_level": {
                "type": "enum",
                "default": "minimal",
                "str_values": ["minimal", "low", "medium", "high"],
            },
            # Local (Ollama) context control: 256K on 12B/26B/31B, 128K on E2B/E4B.
            "num_ctx": {"type": "int", "default": 32768, "min_value": 512, "max_value": 262144},
            # Hosted (OpenRouter/API) output cap.
            "max_tokens": {"type": "int", "default": 4096, "min_value": 1, "max_value": 16384},
        },
        "unsupported_parameters": [],
        "extra_metadata": {
            "reasoning_mode": "optional",
            "lineage": "gemma",
            "developer": "google",
            "context_window": 262144,
            "supports_vision": True,
            "supports_prompt_caching": False,
            "supports_thinking": True,
            "quantization": "Q4_K_M",  # local GGUF default
            "models": [
                "gemma4:e2b",
                "gemma4:e4b",
                "gemma4:12b",
                "gemma4:26b",
                "gemma4:31b",
                "google/gemma-4-31b-it",
                "google/gemma-4-26b-a4b-it",
            ],
        },
    },
]
