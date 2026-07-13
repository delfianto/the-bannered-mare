"""Tests for the per-family tokenizer abstraction (network-free)."""

from types import SimpleNamespace
from typing import Any

import pytest
from src.core.tokenization import get_tokenizer, registry, reset_cache
from src.core.tokenization.backends import HeuristicTokenizer, TiktokenTokenizer


def _family(identifier: str, extra_metadata: dict[str, Any] | None = None) -> Any:
    return SimpleNamespace(family_identifier=identifier, extra_metadata=extra_metadata)


@pytest.fixture(autouse=True)
def _clear_cache():
    reset_cache()
    yield
    reset_cache()


# --- backends ---


def test_tiktoken_counts_and_empty() -> None:
    tok = TiktokenTokenizer("o200k_base")
    assert tok.count("hello world") > 0
    assert tok.count("") == 0


def test_tiktoken_handles_special_token_text() -> None:
    """User/RP content containing <|...|> must not raise."""
    assert TiktokenTokenizer("o200k_base").count("<|endoftext|> hi") > 0


def test_heuristic_is_deterministic() -> None:
    tok = HeuristicTokenizer(chars_per_token=4.0)
    assert tok.count("a" * 8) == 2
    assert tok.count("") == 0
    assert tok.count("x") == 1  # rounds up, min 1


def test_count_messages_includes_overhead() -> None:
    tok = HeuristicTokenizer(chars_per_token=1.0)  # 1 token per char
    # base(3) + [per(3)+4] + [per(3)+2] + priming(3) = 18
    n = tok.count_messages(
        [{"role": "user", "content": "abcd"}, {"role": "assistant", "content": "xy"}]
    )
    assert n == 18


# --- registry resolution ---


def test_openai_family_uses_o200k() -> None:
    tok = get_tokenizer(_family("openai/gpt-4o"))
    assert tok.name == "tiktoken:o200k_base"


def test_anthropic_family_uses_heuristic() -> None:
    tok = get_tokenizer(_family("anthropic/claude-opus-4.8"))
    assert tok.name.startswith("heuristic")


def test_extra_metadata_override_wins() -> None:
    tok = get_tokenizer(
        _family("openai/gpt-4o", {"tokenizer": {"kind": "tiktoken", "encoding": "cl100k_base"}})
    )
    assert tok.name == "tiktoken:cl100k_base"


def test_invalid_override_falls_back_to_default() -> None:
    tok = get_tokenizer(_family("openai/gpt-4o", {"tokenizer": {"kind": "bogus"}}))
    assert tok.name == "tiktoken:o200k_base"


def test_hf_load_failure_degrades_to_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unreachable/gated HF repo must not raise — it degrades to a tiktoken proxy."""

    class _Boom:
        def __init__(self, *_a: object, **_k: object):
            raise RuntimeError("offline")

    monkeypatch.setattr(registry, "HuggingFaceTokenizer", _Boom)
    tok = get_tokenizer(_family("deepseek/deepseek-v4"))
    assert tok.name == "tiktoken:o200k_base"
    assert tok.count("hello") > 0


def test_get_tokenizer_caches_per_family() -> None:
    fam = _family("openai/gpt-4o")
    assert get_tokenizer(fam) is get_tokenizer(fam)


def test_none_family_returns_working_default() -> None:
    tok = get_tokenizer(None)
    assert tok.count("hello world") > 0


def test_families_differ_from_cl100k_baseline() -> None:
    """A family-matched tokenizer should not silently equal the old cl100k default
    for a mixed sample (proves per-family selection actually varies)."""
    sample = "def f(x): return x  # 日本語 テキスト and some prose"
    o200k = get_tokenizer(_family("openai/gpt-4o")).count(sample)
    heuristic = get_tokenizer(_family("anthropic/claude-opus-4.8")).count(sample)
    cl100k = TiktokenTokenizer("cl100k_base").count(sample)
    assert o200k != cl100k or heuristic != cl100k
