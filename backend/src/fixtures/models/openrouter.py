"""OpenRouter model seed data.

Only a small curated subset is `enabled` by default — the models known to be
strong for roleplay, plus the free-tier models (no cost to leave around). The
rest are seeded as disabled "extras": they cost nothing sitting in the table
and save the user from adding them by hand if they want to experiment, since
they're all hosted (no local download either way).
"""

from src.fixtures.models._types import ModelSeedData

# Shared RP sampler for the Llama 3 finetunes/merges (min_p + repetition_penalty
# are the community staples).
_LLAMA_RP = {
    "max_tokens": 4096,
    "temperature": 1.0,
    "top_p": 0.95,
    "top_k": 50,
    "min_p": 0.05,
    "repetition_penalty": 1.05,
}

# Shared RP sampler for TheDrummer's Mistral-based finetunes (Nemo 12B / Small 24B
# lineage) — mirrors the mistral/mistral-nemo & mistral/mistral-small family contract.
_MISTRAL_RP = {
    "max_tokens": 4096,
    "temperature": 0.9,
    "top_p": 0.92,
    "top_k": 65,
    "repeat_penalty": 1.1,
}

OPENROUTER_MODELS: list[ModelSeedData] = [
    # Defaults are curated: the open RP/storytelling finetunes PLUS the
    # community-favorite open-weight families (Gemma, GLM-5.x, DeepSeek, MiMo,
    # Kimi, Poolside) ship enabled; proprietary models and general-purpose
    # non-favorites ship disabled — the user turns those on as needed.
    # Sao10K (-> llama3 family) — RP finetunes; all enabled.
    {
        "name": "Sao10K Euryale 70B v2.3 (L3.3)",
        "model_identifier": "sao10k/l3.3-euryale-70b",
        "family_identifier": "meta/llama-3",
        "provider_type": "openrouter",
        "parameters": {**_LLAMA_RP},
        "enabled": True,
    },
    {
        "name": "Sao10K Hanami X1 70B (L3.1)",
        "model_identifier": "sao10k/l3.1-70b-hanami-x1",
        "family_identifier": "meta/llama-3",
        "provider_type": "openrouter",
        "parameters": {**_LLAMA_RP},
        "enabled": True,
    },
    {
        "name": "Sao10K Lunaris 8B (L3)",
        "model_identifier": "sao10k/l3-lunaris-8b",
        "family_identifier": "meta/llama-3",
        "provider_type": "openrouter",
        "parameters": {**_LLAMA_RP},
        "enabled": True,
    },
    # TheDrummer — Llama/Nemotron lineage (-> llama3 family). RP finetune; enabled.
    {
        "name": "TheDrummer Valkyrie 49B v1",
        "model_identifier": "thedrummer/valkyrie-49b-v1",
        "family_identifier": "meta/llama-3",
        "provider_type": "openrouter",
        "parameters": {**_LLAMA_RP},
        "enabled": True,
    },
    # TheDrummer — Mistral lineage (-> mistral-nemo / mistral-small families).
    # RP finetunes; all enabled.
    {
        "name": "TheDrummer Cydonia 24B v4.1",
        "model_identifier": "thedrummer/cydonia-24b-v4.1",
        "family_identifier": "mistral/mistral-small",
        "provider_type": "openrouter",
        "parameters": {**_MISTRAL_RP},
        "enabled": True,
    },
    {
        "name": "TheDrummer Skyfall 36B v2",
        "model_identifier": "thedrummer/skyfall-36b-v2",
        "family_identifier": "mistral/mistral-small",
        "provider_type": "openrouter",
        "parameters": {**_MISTRAL_RP},
        "enabled": True,
    },
    {
        "name": "TheDrummer UnslopNemo 12B",
        "model_identifier": "thedrummer/unslopnemo-12b",
        "family_identifier": "mistral/mistral-nemo",
        "provider_type": "openrouter",
        "parameters": {**_MISTRAL_RP},
        "enabled": True,
    },
    {
        "name": "TheDrummer Rocinante 12B",
        "model_identifier": "thedrummer/rocinante-12b",
        "family_identifier": "mistral/mistral-nemo",
        "provider_type": "openrouter",
        "parameters": {**_MISTRAL_RP},
        "enabled": True,
    },
    # Other Llama 3 RP finetunes & merges — enabled by default.
    {
        "name": "NeverSleep Lumimaid 70B (L3.1)",
        "model_identifier": "neversleep/llama-3.1-lumimaid-70b",
        "family_identifier": "meta/llama-3",
        "provider_type": "openrouter",
        "parameters": {**_LLAMA_RP},
        "enabled": True,
    },
    {
        "name": "TheDrummer Anubis 70B (L3.3)",
        "model_identifier": "thedrummer/anubis-70b-v1.1",
        "family_identifier": "meta/llama-3",
        "provider_type": "openrouter",
        "parameters": {**_LLAMA_RP},
        "enabled": True,
    },
    {
        "name": "Nous Hermes 3 70B (L3.1)",
        "model_identifier": "nousresearch/hermes-3-llama-3.1-70b",
        "family_identifier": "meta/llama-3",
        "provider_type": "openrouter",
        "parameters": {**_LLAMA_RP},
        "enabled": True,
    },
    # DeepSeek — community favorites: R1, V3.2, V4 Pro/Flash enabled; Chat V3.1 disabled.
    {
        "name": "DeepSeek V4 Pro",
        "model_identifier": "deepseek/deepseek-v4-pro",
        "family_identifier": "deepseek/deepseek-v4",
        "provider_type": "openrouter",
        "parameters": {"temperature": 1.0, "top_p": 0.95, "max_tokens": 4096},
        "enabled": True,
    },
    {
        "name": "DeepSeek V4 Flash",
        "model_identifier": "deepseek/deepseek-v4-flash",
        "family_identifier": "deepseek/deepseek-v4",
        "provider_type": "openrouter",
        "parameters": {"temperature": 1.0, "top_p": 0.95, "max_tokens": 4096},
        "enabled": True,
    },
    {
        "name": "DeepSeek V3.2",
        "model_identifier": "deepseek/deepseek-v3.2",
        "family_identifier": "deepseek/deepseek-v3",
        "provider_type": "openrouter",
        "parameters": {"temperature": 1.0, "top_p": 0.95, "max_tokens": 4096},
        "enabled": True,
    },
    {
        "name": "DeepSeek Chat V3.1",
        "model_identifier": "deepseek/deepseek-chat-v3.1",
        "family_identifier": "deepseek/deepseek-v3",
        "provider_type": "openrouter",
        "parameters": {"temperature": 1.0, "top_p": 0.95, "max_tokens": 4096},
        "enabled": False,
    },
    {
        # Reasoner: temperature/top_p are ignored by deepseek-reasoner; keep output bounded.
        "name": "DeepSeek R1",
        "model_identifier": "deepseek/deepseek-r1",
        "family_identifier": "deepseek/deepseek-r1",
        "provider_type": "openrouter",
        "parameters": {"max_tokens": 8192},
        "enabled": True,
    },
    # GLM (Zhipu) — GLM-5.x enabled by default; 4.x disabled.
    {
        "name": "GLM 5.2",
        "model_identifier": "z-ai/glm-5.2",
        "family_identifier": "zai/glm-5",
        "provider_type": "openrouter",
        "parameters": {"temperature": 0.8, "top_p": 0.95, "max_tokens": 4096},
        "enabled": True,
    },
    {
        "name": "GLM 5.1",
        "model_identifier": "z-ai/glm-5.1",
        "family_identifier": "zai/glm-5",
        "provider_type": "openrouter",
        "parameters": {"temperature": 0.8, "top_p": 0.95, "max_tokens": 4096},
        "enabled": True,
    },
    {
        "name": "GLM 5",
        "model_identifier": "z-ai/glm-5",
        "family_identifier": "zai/glm-5",
        "provider_type": "openrouter",
        "parameters": {"temperature": 0.8, "top_p": 0.95, "max_tokens": 4096},
        "enabled": True,
    },
    {
        "name": "GLM 4.7 Flash",
        "model_identifier": "z-ai/glm-4.7-flash",
        "family_identifier": "zai/glm-4",
        "provider_type": "openrouter",
        "parameters": {"temperature": 0.8, "top_p": 0.95, "max_tokens": 4096},
        "enabled": False,
    },
    {
        "name": "GLM 4.7",
        "model_identifier": "z-ai/glm-4.7",
        "family_identifier": "zai/glm-4",
        "provider_type": "openrouter",
        "parameters": {"temperature": 0.8, "top_p": 0.95, "max_tokens": 4096},
        "enabled": False,
    },
    {
        "name": "GLM 4.5 Air (Free)",
        "model_identifier": "z-ai/glm-4.5-air:free",
        "family_identifier": "zai/glm-4",
        "provider_type": "openrouter",
        "parameters": {"temperature": 0.8, "top_p": 0.95, "max_tokens": 4096},
        "enabled": False,
    },
    # MiniMax — extras, disabled by default.
    {
        "name": "MiniMax M3",
        "model_identifier": "minimax/minimax-m3",
        "family_identifier": "minimax/minimax-m3",
        "provider_type": "openrouter",
        "parameters": {"temperature": 1.0, "top_p": 0.95, "max_tokens": 4096},
        "enabled": False,
    },
    {
        "name": "MiniMax M2.7",
        "model_identifier": "minimax/minimax-m2.7",
        "family_identifier": "minimax/minimax-m2",
        "provider_type": "openrouter",
        "parameters": {"temperature": 1.0, "top_p": 0.95, "top_k": 40, "max_tokens": 4096},
        "enabled": False,
    },
    {
        "name": "MiniMax M2.5",
        "model_identifier": "minimax/minimax-m2.5",
        "family_identifier": "minimax/minimax-m2",
        "provider_type": "openrouter",
        "parameters": {"temperature": 1.0, "top_p": 0.95, "top_k": 40, "max_tokens": 4096},
        "enabled": False,
    },
    # Kimi (Moonshot) — K-series enabled by default.
    {
        "name": "Moonshot Kimi K2.6",
        "model_identifier": "moonshotai/kimi-k2.6",
        "family_identifier": "moonshot/kimi-k2",
        "provider_type": "openrouter",
        "parameters": {"temperature": 0.6, "top_p": 1.0, "max_tokens": 8192},
        "enabled": True,
    },
    {
        "name": "Moonshot Kimi K2.6 (Free)",
        "model_identifier": "moonshotai/kimi-k2.6:free",
        "family_identifier": "moonshot/kimi-k2",
        "provider_type": "openrouter",
        "parameters": {"temperature": 0.6, "top_p": 1.0, "max_tokens": 8192},
        "enabled": False,
    },
    {
        "name": "Moonshot Kimi K2.5",
        "model_identifier": "moonshotai/kimi-k2.5",
        "family_identifier": "moonshot/kimi-k2",
        "provider_type": "openrouter",
        "parameters": {"temperature": 0.6, "top_p": 1.0, "max_tokens": 8192},
        "enabled": True,
    },
    # Misc free models — disabled by default.
    {
        "name": "Arcee Trinity Large (Free)",
        "model_identifier": "arcee-ai/trinity-large-preview:free",
        "family_identifier": "openrouter/misc",
        "provider_type": "openrouter",
        "parameters": {"temperature": 0.85, "top_p": 0.9, "max_tokens": 4096},
        "enabled": False,
    },
    # Qwen 3.6 Plus (Free) removed — no longer a free-tier model on OpenRouter.
    # Xiaomi MiMo (-> mimo-v2.5 family) — enabled by default.
    {
        "name": "Xiaomi MiMo V2.5",
        "model_identifier": "xiaomi/mimo-v2.5",
        "family_identifier": "xiaomi/mimo-v2.5",
        "provider_type": "openrouter",
        "parameters": {"temperature": 1.0, "top_p": 0.95, "max_tokens": 4096},
        "enabled": True,
    },
    {
        "name": "Xiaomi MiMo V2.5 Pro",
        "model_identifier": "xiaomi/mimo-v2.5-pro",
        "family_identifier": "xiaomi/mimo-v2.5",
        "provider_type": "openrouter",
        # Pro adds top_k / min_p over the base V2.5.
        "parameters": {
            "temperature": 1.0,
            "top_p": 0.95,
            "top_k": 40,
            "min_p": 0.0,
            "max_tokens": 4096,
        },
        "enabled": True,
    },
    # Poolside Laguna (Free) — enabled by default.
    {
        "name": "Poolside Laguna M.1 (Free)",
        "model_identifier": "poolside/laguna-m.1:free",
        "family_identifier": "poolside/laguna",
        "provider_type": "openrouter",
        "parameters": {"temperature": 0.8, "max_tokens": 4096},
        "enabled": True,
    },
    {
        "name": "Poolside Laguna XS.2 (Free)",
        "model_identifier": "poolside/laguna-xs.2:free",
        "family_identifier": "poolside/laguna",
        "provider_type": "openrouter",
        "parameters": {"temperature": 0.8, "max_tokens": 4096},
        "enabled": True,
    },
    # Google Gemma (Free) — enabled by default.
    {
        "name": "Gemma 4 31B IT (Free)",
        "model_identifier": "google/gemma-4-31b-it:free",
        "family_identifier": "google/gemma-4",
        "provider_type": "openrouter",
        "parameters": {"temperature": 0.8, "top_p": 0.9, "max_tokens": 4096},
        "enabled": True,
    },
    {
        "name": "Gemma 4 26B A4B IT (Free)",
        "model_identifier": "google/gemma-4-26b-a4b-it:free",
        "family_identifier": "google/gemma-4",
        "provider_type": "openrouter",
        "parameters": {"temperature": 0.8, "top_p": 0.9, "max_tokens": 4096},
        "enabled": True,
    },
]
