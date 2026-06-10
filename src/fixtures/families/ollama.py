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
    {
        "name": "Gemma 4",
        "family_identifier": "ollama/gemma-4",
        "description": (
            "Google Gemma 4 for local deployment (E2B, E4B, 12B, 26B A4B MoE, 31B). "
            "Multimodal, 128K-256K context, thinking mode via <|think|> system token."
        ),
        "provider_types": ["ollama"],
        "parameters": {
            # Official Gemma 4 sampling guidance: temperature=1.0, top_p=0.95, top_k=64
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min_value": 0.0,
                "max_value": 2.0,
            },
            "top_p": {
                "type": "float",
                "default": 0.95,
                "min_value": 0.0,
                "max_value": 1.0,
            },
            "top_k": {
                "type": "int",
                "default": 64,
                "min_value": 1,
                "max_value": 200,
            },
            # 256K max on 12B/26B/31B; E2B/E4B cap at 128K
            "num_ctx": {
                "type": "int",
                "default": 32768,
                "min_value": 512,
                "max_value": 262144,
            },
        },
        "extra_metadata": {
            "context_window": 262144,
            "supports_vision": True,
            "supports_thinking": True,
            "quantization": "Q4_K_M",
            "models": [
                "gemma4:e2b",
                "gemma4:e4b",
                "gemma4:12b",
                "gemma4:26b",
                "gemma4:31b",
            ],
        },
    },
]
