"""Tests for the auxiliary-call reasoning-suppression override."""

from typing import Any

from src.core.persistence.enums import ProviderType
from src.provider.reasoning import family_supports_reasoning, reasoning_off_override

# Minimal family-parameter shapes mirroring the seed definitions.
_GPT5_REASONING = {"reasoning_effort": {"type": "enum", "str_values": ["minimal", "low", "high"]}}
_GEMMA = {"thinking_level": {"type": "enum", "str_values": ["minimal", "low", "medium", "high"]}}
_GEMINI_25 = {"thinking_budget": {"type": "int", "min_value": 0, "max_value": 24576}}
_CLAUDE = {"thinking": {"type": "object", "properties": {"type": {"str_values": ["disabled"]}}}}
_NON_REASONING = {"temperature": {"type": "float", "default": 1.0}, "max_tokens": {"type": "int"}}


def test_family_supports_reasoning() -> None:
    assert family_supports_reasoning(_GEMMA)
    assert family_supports_reasoning(_GPT5_REASONING)
    assert family_supports_reasoning(_CLAUDE)
    assert family_supports_reasoning(_GEMINI_25)
    assert not family_supports_reasoning(_NON_REASONING)
    assert not family_supports_reasoning(None)
    assert not family_supports_reasoning({})


def test_non_reasoning_family_emits_nothing() -> None:
    """A model that declares no reasoning control must never receive a reasoning
    parameter — sending one 400s on providers like native OpenAI."""
    for pt in (ProviderType.OPENAI, ProviderType.ANTHROPIC, ProviderType.GOOGLE):
        assert reasoning_off_override(_NON_REASONING, pt) == {}
    assert reasoning_off_override(None, ProviderType.OPENAI) == {}


def test_anthropic_disables_thinking() -> None:
    assert reasoning_off_override(_CLAUDE, ProviderType.ANTHROPIC) == {
        "thinking": {"type": "disabled"}
    }


def test_google_uses_declared_thinking_control() -> None:
    assert reasoning_off_override(_GEMMA, ProviderType.GOOGLE) == {"thinking_level": "minimal"}
    assert reasoning_off_override(_GEMINI_25, ProviderType.GOOGLE) == {"thinking_budget": 0}


def test_openai_compatible_uses_reasoning_effort() -> None:
    """Gemma served over an OpenAI-compatible transport (LM Studio/OpenRouter)
    can't use thinking_level (the OpenAI adapter drops it), so we emit the
    universal reasoning_effort instead."""
    for pt in (
        ProviderType.OPENAI,
        ProviderType.OPENROUTER,
        ProviderType.LMSTUDIO,
        ProviderType.OPENCODE,
        ProviderType.OPENCODE_GO,
        ProviderType.XAI,
        ProviderType.CUSTOM,
    ):
        assert reasoning_off_override(_GEMMA, pt) == {"reasoning_effort": "none"}
        assert reasoning_off_override(_GPT5_REASONING, pt) == {"reasoning_effort": "none"}


def test_openai_compatible_thinking_family_maps_to_thinking() -> None:
    """Open-weight families carrying a `thinking` object map to the adapter's
    reasoning.enabled=false, so emit the thinking object rather than effort."""
    assert reasoning_off_override(_CLAUDE, ProviderType.OPENROUTER) == {
        "thinking": {"type": "disabled"}
    }


def test_unknown_transport_emits_nothing() -> None:
    """Ollama has no known-safe control here — emit nothing rather than risk a 400."""
    assert reasoning_off_override(_GEMMA, ProviderType.OLLAMA) == {}


def test_override_is_plain_dict() -> None:
    """Returned override must be a fresh mutable dict the caller can merge."""
    out: dict[str, Any] = reasoning_off_override(_GEMMA, ProviderType.LMSTUDIO)
    out["extra"] = 1  # must not raise
