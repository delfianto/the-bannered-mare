"""Unit tests for the pure discovery filters (no service/repo/provider needed)."""

from src.provider.discovery_filters import (
    apply_allow_list,
    dedupe_preserving_order,
    filter_blacklisted,
)
from src.provider.schemas import DiscoveredModel


def _models(*identifiers: str) -> list[DiscoveredModel]:
    return [DiscoveredModel(identifier=i, display_name=i, state="loaded") for i in identifiers]


def test_filter_drops_openai_dated_snapshots_keeps_chat_latest() -> None:
    """Dated GPT snapshots are dropped; "-chat-latest" aliases are kept.

    The chat SKUs are only callable via "-chat-latest" (no bare form), so the
    filter must not treat them like the redundant dated snapshots.
    """
    models = _models(
        "gpt-5-2025-08-07",  # dated snapshot -> dropped
        "gpt-5.4-2026-03-05",  # dated snapshot -> dropped
        "gpt-5.4-mini-2026-03-17",  # dated snapshot -> dropped
        "gpt-5-chat-latest",  # only callable form of the chat SKU -> kept
        "gpt-5.3-chat-latest",  # kept
        "gpt-5.4-pro",  # kept
        "gpt-4o",  # kept
        "claude-sonnet-4-5-20250929",  # non-GPT dated -> untouched, kept
    )

    kept = {m.identifier for m in filter_blacklisted(models)}

    assert kept == {
        "gpt-5-chat-latest",
        "gpt-5.3-chat-latest",
        "gpt-5.4-pro",
        "gpt-4o",
        "claude-sonnet-4-5-20250929",
    }


def test_filter_drops_openai_o_series_reasoning_by_prefix() -> None:
    """o1/o3/o4 reasoning models are dropped; an "o1" *inside* a name is not."""
    kept = {m.identifier for m in filter_blacklisted(_models("o1", "o3-mini", "sao10k/euryale"))}
    assert kept == {"sao10k/euryale"}


def test_dedupe_preserving_order_trims_blanks_and_dupes() -> None:
    assert dedupe_preserving_order(["b", "b", "  ", " a ", "b", "a"]) == ["b", "a"]


def test_apply_allow_list_empty_keeps_all() -> None:
    models = _models("a:1", "b:2")
    assert apply_allow_list(None, models) == models
    assert apply_allow_list([], models) == models


def test_apply_allow_list_keeps_only_listed() -> None:
    kept = apply_allow_list(["a:1"], _models("a:1", "b:2"))
    assert [m.identifier for m in kept] == ["a:1"]
