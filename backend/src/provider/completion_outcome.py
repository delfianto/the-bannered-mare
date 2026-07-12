"""Classify a completion's outcome from its structured signals — provider-agnostic.

Detects non-answers (empty, content-filtered, truncated, reasoning-only) so the
chat layer can surface a clear message instead of a silent blank reply. Relies on
two signals only:

1. Usable content — after stripping, is there any text (or a tool call)?
2. The adapter-normalized ``finish_reason`` vocabulary (``stop`` / ``length`` /
   ``content_filter`` / ``refusal`` / ``tool_calls`` / …).

It deliberately does NOT scan output text for refusal phrases ("I'm sorry",
"as an AI", "无法", …): those are locale- and model-specific and would false-flag
an in-character refusal. Every provider's safety/length terminals are mapped into
the shared vocabulary by the adapters, so this stays generic across models.
"""

import enum

# Normalized finish_reason values that mean "the provider blocked/refused output".
# The adapters map their native reasons into these (Gemini SAFETY/RECITATION/…,
# Anthropic refusal, OpenAI/OpenRouter content_filter).
_FILTER_REASONS = frozenset(
    {"content_filter", "refusal", "safety", "recitation", "blocklist", "prohibited_content", "spii"}
)
_LENGTH_REASONS = frozenset({"length", "max_tokens"})


class CompletionOutcome(enum.StrEnum):
    """Normalized result of a completion. ``value`` doubles as the audit status."""

    USABLE = "usable"  # has real content (or a tool call) — deliver it
    FILTERED = "filtered"  # provider safety filter refused/blocked the response
    TRUNCATED = "truncated"  # hit the token cap before producing an answer
    REASONING_ONLY = "reasoning_only"  # spent the budget reasoning, no answer text
    EMPTY = "empty"  # returned nothing with no clear reason (soft filter / degenerate)


def _is_filter(finish_reason: str | None) -> bool:
    return bool(finish_reason) and finish_reason.lower() in _FILTER_REASONS


def classify_completion(
    content: str | None,
    reasoning: str | None,
    finish_reason: str | None,
    *,
    has_tool_calls: bool = False,
) -> CompletionOutcome:
    """Classify a completion into a normalized outcome (see CompletionOutcome)."""
    has_text = bool((content or "").strip())

    # A filter terminal means the output is a refusal/block, not a real reply —
    # treat it as FILTERED even when the provider returned the refusal AS content
    # (e.g. a canned "I can't help with that"). Tool calls are never filtered.
    if _is_filter(finish_reason) and not has_tool_calls:
        return CompletionOutcome.FILTERED

    if has_text or has_tool_calls:
        return CompletionOutcome.USABLE

    # No usable content — determine why so the caller can advise the user.
    if finish_reason and finish_reason.lower() in _LENGTH_REASONS:
        return CompletionOutcome.TRUNCATED
    if (reasoning or "").strip():
        return CompletionOutcome.REASONING_ONLY
    return CompletionOutcome.EMPTY
