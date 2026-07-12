"""Reasoning-suppression override for auxiliary task-model calls.

Titles, tone chips, and reply suggestions are throwaway scaffolding — the user
picks one, edits it, or ignores it. Thinking-capable models otherwise burn
hundreds of *reasoning* tokens producing them (a prompt instruction can't stop a
hard thinking model; only a provider parameter can). This module derives the
parameter that minimizes reasoning for such calls, chosen so that:

* it is only emitted when the model's family actually declares a reasoning
  control — a non-reasoning model (gpt-4, deepseek-chat) gets ``{}`` so nothing
  unsupported is sent (no 400s), and
* it uses a field the route's transport adapter already forwards, so no adapter
  allowlist changes are needed and the main chat path is untouched.
"""

from typing import Any

from src.core.persistence.enums import ProviderType

# Family parameter keys that signal a model can reason. Presence of any one gates
# the whole override — its absence means "not a reasoning model, send nothing".
_REASONING_KEYS = ("reasoning_effort", "thinking", "thinking_level", "thinking_budget")

# OpenAI-compatible transports (share OpenAIAdapter, which forwards
# ``reasoning_effort`` and maps a ``thinking`` object to ``reasoning.enabled``).
_OPENAI_COMPATIBLE = frozenset(
    {
        ProviderType.OPENAI,
        ProviderType.XAI,
        ProviderType.OPENROUTER,
        ProviderType.OPENCODE,
        ProviderType.OPENCODE_GO,
        ProviderType.LMSTUDIO,
        ProviderType.CUSTOM,
    }
)


def family_supports_reasoning(family_parameters: dict[str, Any] | None) -> bool:
    """True when the family declares any reasoning-control parameter."""
    if not family_parameters:
        return False
    return any(key in family_parameters for key in _REASONING_KEYS)


def reasoning_off_override(
    family_parameters: dict[str, Any] | None, provider_type: ProviderType
) -> dict[str, Any]:
    """Parameter(s) that minimize reasoning for a throwaway auxiliary call.

    Returns ``{}`` for non-reasoning families and for transports where we have no
    safe control (Ollama), so it can be merged unconditionally.
    """
    if not family_supports_reasoning(family_parameters):
        return {}
    assert family_parameters is not None  # narrowed by family_supports_reasoning

    if provider_type == ProviderType.ANTHROPIC:
        # AnthropicAdapter forwards the thinking object verbatim.
        return {"thinking": {"type": "disabled"}}

    if provider_type == ProviderType.GOOGLE:
        # GeminiAdapter forwards thinking_level (3.x) and thinking_budget (2.5);
        # they are mutually exclusive, so pick whichever the family declares.
        if "thinking_level" in family_parameters:
            return {"thinking_level": "minimal"}
        if "thinking_budget" in family_parameters:
            return {"thinking_budget": 0}
        return {}

    if provider_type in _OPENAI_COMPATIBLE:
        # Open-weight families carrying a `thinking` object map to the adapter's
        # `reasoning.enabled=false` (a clean disable); everything else uses
        # `reasoning_effort: "none"`. "none" is the only value that actually
        # disables reasoning on local servers (LM Studio honors it; the graded
        # minimal/low/medium tiers still reason), and it is valid on current
        # GPT-5.1/5.2. Older reasoning-only models (o1/o3) reject "none" — an
        # unusual pick for a throwaway task model, and the family gate keeps it
        # away from non-reasoning models entirely.
        if "thinking" in family_parameters:
            return {"thinking": {"type": "disabled"}}
        return {"reasoning_effort": "none"}

    # OLLAMA and any future transport without a known-safe control.
    return {}
