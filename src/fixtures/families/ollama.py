"""Ollama (local GGUF) model family seed data."""

from src.fixtures.model_families import ModelFamilySeedData


def _ollama_family(
    name: str,
    identifier: str,
    description: str,
    *,
    temp_default: float = 0.8,
    ctx_default: int = 8192,
    ctx_max: int = 131072,
) -> ModelFamilySeedData:
    """Build an Ollama family with minimal boilerplate."""
    return {
        "name": name,
        "family_identifier": identifier,
        "description": description,
        "provider_types": ["ollama"],
        "parameters": {
            "temperature": {
                "type": "float",
                "default": temp_default,
                "min_value": 0.0,
                "max_value": 2.0,
            },
            "num_ctx": {
                "type": "int",
                "default": ctx_default,
                "min_value": 512,
                "max_value": ctx_max,
            },
        },
        "extra_metadata": {
            "context_window": ctx_default,
            "quantization": "Q4_K_M",
        },
    }


OLLAMA_FAMILIES: list[ModelFamilySeedData] = [
    _ollama_family(
        "TheDrummer Roleplay",
        "ollama/thedrummer-rp",
        "TheDrummer's RP-optimized models (Cydonia, Skyfall, Rocinante)",
        temp_default=0.85,
        ctx_max=32768,
    ),
    _ollama_family(
        "Gemma 4",
        "ollama/gemma-4",
        "Google Gemma 4 family for local deployment (4B, 12B, 27B)",
        temp_default=0.7,
        ctx_default=32768,
        ctx_max=128000,
    ),
]
