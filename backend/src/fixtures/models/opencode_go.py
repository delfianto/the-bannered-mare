"""OpenCode Go model seed data — bare identifiers for open-weight SKUs.

These deliberately overlap the OpenRouter open-weight models: OpenCode Go names
them without the vendor prefix (``deepseek-v4-pro`` vs ``deepseek/deepseek-v4-pro``),
so seeding folds them into the *same* canonical model as a second route —
demonstrating one model reachable through two providers.
"""

from src.fixtures.models._types import ModelSeedData

OPENCODE_GO_MODELS: list[ModelSeedData] = [
    {
        "name": "DeepSeek V4 Pro",
        "model_identifier": "deepseek-v4-pro",
        "family_identifier": "deepseek/deepseek-v4",
        "provider_type": "opencode_go",
        "parameters": {"temperature": 1.0, "top_p": 0.95, "max_tokens": 4096},
        "enabled": True,
    },
    {
        "name": "DeepSeek V4 Flash",
        "model_identifier": "deepseek-v4-flash",
        "family_identifier": "deepseek/deepseek-v4",
        "provider_type": "opencode_go",
        "parameters": {"temperature": 1.0, "top_p": 0.95, "max_tokens": 4096},
        "enabled": True,
    },
    {
        "name": "GLM 5.2",
        "model_identifier": "glm-5.2",
        "family_identifier": "zai/glm-5",
        "provider_type": "opencode_go",
        "parameters": {"temperature": 0.8, "top_p": 0.95, "max_tokens": 4096},
        "enabled": True,
    },
    {
        "name": "GLM 5.1",
        "model_identifier": "glm-5.1",
        "family_identifier": "zai/glm-5",
        "provider_type": "opencode_go",
        "parameters": {"temperature": 0.8, "top_p": 0.95, "max_tokens": 4096},
        "enabled": True,
    },
    {
        # Plain GLM 5 is not in the OpenCode Go catalog — route present but off.
        "name": "GLM 5",
        "model_identifier": "glm-5",
        "family_identifier": "zai/glm-5",
        "provider_type": "opencode_go",
        "parameters": {"temperature": 0.8, "top_p": 0.95, "max_tokens": 4096},
        "enabled": False,
    },
    {
        "name": "MiniMax M3",
        "model_identifier": "minimax-m3",
        "family_identifier": "minimax/minimax-m3",
        "provider_type": "opencode_go",
        "parameters": {"temperature": 1.0, "top_p": 0.95, "max_tokens": 4096},
        "enabled": True,
    },
    {
        "name": "MiniMax M2.7",
        "model_identifier": "minimax-m2.7",
        "family_identifier": "minimax/minimax-m2",
        "provider_type": "opencode_go",
        "parameters": {"temperature": 1.0, "top_p": 0.95, "top_k": 40, "max_tokens": 4096},
        "enabled": True,
    },
    {
        "name": "Moonshot Kimi K2.6",
        "model_identifier": "kimi-k2.6",
        "family_identifier": "moonshot/kimi-k2",
        "provider_type": "opencode_go",
        "parameters": {"temperature": 0.6, "top_p": 1.0, "max_tokens": 8192},
        "enabled": True,
    },
    {
        # Coding-focused Kimi SKU; OpenCode-Go-only (no OpenRouter/native route).
        "name": "Moonshot Kimi K2.7 Code",
        "model_identifier": "kimi-k2.7-code",
        "family_identifier": "moonshot/kimi-k2",
        "provider_type": "opencode_go",
        "parameters": {"temperature": 0.6, "top_p": 1.0, "max_tokens": 8192},
        "enabled": True,
    },
    {
        "name": "Xiaomi MiMo V2.5",
        "model_identifier": "mimo-v2.5",
        "family_identifier": "xiaomi/mimo-v2.5",
        "provider_type": "opencode_go",
        "parameters": {"temperature": 1.0, "top_p": 0.95, "max_tokens": 4096},
        "enabled": True,
    },
    {
        "name": "Xiaomi MiMo V2.5 Pro",
        "model_identifier": "mimo-v2.5-pro",
        "family_identifier": "xiaomi/mimo-v2.5",
        "provider_type": "opencode_go",
        "parameters": {"temperature": 1.0, "top_p": 0.95, "max_tokens": 4096},
        "enabled": True,
    },
]
