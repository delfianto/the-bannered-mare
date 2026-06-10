"""Zhipu / Z.ai GLM model family seed data (base-model-generation keyed).

GLM is grouped by generation: GLM-4 (4.5 / 4.6 / 4.7, incl. Air & Flash) and
GLM-5 (5 / 5.1, incl. Turbo). Both share the GLM signature — temperature capped
at 1.0 (not 2.0), top_p default 0.95, a hybrid `thinking` toggle, and an
OpenAI-compatible sampling surface. GLM-5 adds a larger context window and the
`reasoning_effort` control (GLM-5.1). Routed via OpenRouter (`z-ai/glm-*`).

Parameter ranges/defaults follow the Z.ai Chat Completion API docs
(docs.z.ai/api-reference/llm/chat-completion).
"""

from src.fixtures.model_families import ModelFamilySeedData

# Shared GLM sampling surface. Temperature is capped at 1.0 (GLM-specific, unlike
# the 2.0 cap elsewhere); `thinking` is the hybrid-reasoning toggle
# (Z.ai shape: thinking={"type": "enabled"|"disabled"}).
_GLM_BASE: dict = {
    "temperature": {"type": "float", "default": 1.0, "min_value": 0.0, "max_value": 1.0},
    "top_p": {"type": "float", "default": 0.95, "min_value": 0.01, "max_value": 1.0},
    "top_k": {"type": "int", "default": 40, "min_value": 1, "max_value": 100},
    "thinking": {
        "type": "object",
        "properties": {
            "type": {"type": "enum", "str_values": ["enabled", "disabled"]},
        },
    },
}

GLM_FAMILIES: list[ModelFamilySeedData] = [
    {
        "name": "GLM 4",
        "family_identifier": "zai/glm-4",
        "description": (
            "Zhipu/Z.ai GLM-4.5 / 4.6 / 4.7 (incl. Air, Flash). Hybrid thinking, "
            "temperature capped at 1.0, 200K context. Routed via OpenRouter."
        ),
        "provider_types": ["openrouter"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 4096, "min_value": 1, "max_value": 128000},
            **_GLM_BASE,
        },
        "unsupported_parameters": [],
        "extra_metadata": {
            "lineage": "glm",
            "developer": "zhipu",
            "context_window": 200000,
            "supports_vision": False,
            "supports_function_calling": True,
            # `thinking` auto-decides on 4.5/4.6; thinks compulsorily when enabled on 4.7.
            "thinking_behavior": "auto on 4.5/4.6, forced-when-enabled on 4.7",
            "models": ["z-ai/glm-4.7", "z-ai/glm-4.7-flash", "z-ai/glm-4.5-air"],
        },
    },
    {
        "name": "GLM 5",
        "family_identifier": "zai/glm-5",
        "description": (
            "Zhipu/Z.ai GLM-5 / 5.1 (incl. Turbo). Forced thinking with reasoning_effort "
            "(GLM-5.1), temperature capped at 1.0, up to ~262K context. Routed via OpenRouter."
        ),
        "provider_types": ["openrouter"],
        "parameters": {
            "max_tokens": {"type": "int", "default": 4096, "min_value": 1, "max_value": 128000},
            # GLM-5.1 only; GLM-5 / 5-Turbo simply omit it.
            "reasoning_effort": {
                "type": "enum",
                "default": "medium",
                "str_values": ["low", "medium", "high"],
            },
            **_GLM_BASE,
        },
        "unsupported_parameters": [],
        "extra_metadata": {
            "lineage": "glm",
            "developer": "zhipu",
            "context_window": 262144,
            "supports_vision": False,
            "supports_function_calling": True,
            "thinking_behavior": "forced when enabled (5 / 5.1 / Turbo)",
            "models": ["z-ai/glm-5", "z-ai/glm-5.1"],
        },
    },
]
