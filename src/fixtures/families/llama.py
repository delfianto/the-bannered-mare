"""Meta Llama 3 model family seed data (base-model lineage).

One family spanning Llama 3 / 3.1 / 3.3 and the community RP finetunes & merges
built on them — they share the same sampler contract. The base generation only
changes the context window (classic Llama-3 finetunes are 8K; 3.1/3.3 are 128K),
which is metadata, not a parameter break. RP enthusiasts favor the min_p +
repetition_penalty sampler here. Run locally (Ollama/vLLM GGUF) or hosted
(OpenRouter / niche RP providers).

Bases verified via the HuggingFace model cards (Euryale v2.2 = L3.1, Stheno
v3.4 = L3.1 / v3.2 = L3, Anubis 70B = L3.3, Lunaris = L3 merge).
"""

from src.fixtures.model_families import ModelFamilySeedData
from src.fixtures.parameter_definitions import TEMPERATURE, TOP_K, TOP_P_95

LLAMA_FAMILIES: list[ModelFamilySeedData] = [
    {
        "name": "Llama 3",
        "family_identifier": "meta/llama-3",
        "description": (
            "Meta Llama 3 / 3.1 / 3.3 and the community RP finetunes & merges built on them "
            "(Sao10K Euryale & Stheno, NeverSleep Lumimaid, TheDrummer Anubis, Steelskull "
            "Nevoria, Nous Hermes 3, Lunaris). Classic Llama-3 finetunes are 8K context; "
            "3.1/3.3 are 128K. Run locally (Ollama/vLLM) or hosted (OpenRouter)."
        ),
        "provider_types": ["ollama", "openrouter"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 4096, "min_value": 1, "max_value": 16384},
            "temperature": TEMPERATURE,
            "top_p": TOP_P_95,
            "top_k": {**TOP_K, "default": 50, "max_value": 200},
            # min_p + repetition_penalty are the RP-community staples for Llama samplers.
            "min_p": {"type": "float", "default": 0.05, "min_value": 0.0, "max_value": 1.0},
            "repetition_penalty": {
                "type": "float",
                "default": 1.05,
                "min_value": 1.0,
                "max_value": 2.0,
            },
            # Local (Ollama) context control; hosted output is capped by max_tokens above.
            "num_ctx": {"type": "int", "default": 8192, "min_value": 512, "max_value": 131072},
        },
        "unsupported_parameters": [],
        "extra_metadata": {
            "lineage": "llama",
            "developer": "meta + community",
            # 3.1/3.3 are 128K; classic Llama-3 finetunes (Stheno v3.2, Euryale v2.1,
            # Lunaris) cap at 8K.
            "context_window": 131072,
            "supports_vision": False,
            "supports_function_calling": False,
            "notable_finetunes": {
                "Sao10K Euryale": "L3 v2.1 (70B/8K), L3.1 v2.2 (70B/128K), L3.3 v2.3 (70B/128K) — RP/creative flagship",
                "Sao10K Stheno": "L3 v3.2 (8B/8K), L3.1 v3.4 (8B) — beloved small-model RP",
                "Sao10K Lunaris": "L3 8B merge (Stheno 3.2 + others) — reliable L3 RP",
                "NeverSleep Lumimaid": "L3.1 8B/70B — RP/ERP finetune",
                "TheDrummer Anubis": "L3.3 70B — strong character adherence",
                "Steelskull Nevoria": "L3.3 70B merge",
                "Nous Hermes 3": "L3.1 8B/70B/405B — steerable, strong instruction following",
            },
            "models": [
                "sao10k/l3-euryale-70b",
                "sao10k/l3.1-euryale-70b",
                "sao10k/l3.3-euryale-70b",
                "neversleep/llama-3.1-lumimaid-70b",
                "thedrummer/anubis-70b-v1.1",
                "nousresearch/hermes-3-llama-3.1-70b",
                "sao10k/l3-lunaris-8b",
            ],
        },
    },
]
