"""Tests for the provider-agnostic completion-outcome classifier."""

from src.provider.completion_outcome import CompletionOutcome, classify_completion


def test_content_present_is_usable() -> None:
    assert classify_completion("Hello there.", None, "stop") == CompletionOutcome.USABLE


def test_partial_content_with_length_is_still_usable() -> None:
    # A truncated-but-non-empty reply is worth keeping; only empty length is TRUNCATED.
    assert classify_completion("A half-written rep", None, "length") == CompletionOutcome.USABLE


def test_empty_content_filter_is_filtered() -> None:
    assert classify_completion("", None, "content_filter") == CompletionOutcome.FILTERED
    assert classify_completion(None, None, "content_filter") == CompletionOutcome.FILTERED


def test_refusal_as_content_is_filtered() -> None:
    # The refusal text returned AS the message must not be shown as an RP reply.
    assert classify_completion("你好，我无法给到相关内容。", None, "content_filter") == (
        CompletionOutcome.FILTERED
    )
    # Anthropic 'refusal' normalizes to content_filter upstream, but guard the raw too.
    assert classify_completion("I can't help with that.", None, "refusal") == (
        CompletionOutcome.FILTERED
    )


def test_empty_length_is_truncated() -> None:
    assert classify_completion("", None, "length") == CompletionOutcome.TRUNCATED
    assert classify_completion("", None, "max_tokens") == CompletionOutcome.TRUNCATED


def test_reasoning_only_is_reasoning_only() -> None:
    assert classify_completion("", "let me think...", "stop") == CompletionOutcome.REASONING_ONLY


def test_empty_stop_is_empty() -> None:
    # The DeepSeek soft-filter case: content null, finish stop, no reason.
    assert classify_completion(None, None, "stop") == CompletionOutcome.EMPTY
    assert classify_completion("", None, None) == CompletionOutcome.EMPTY


def test_whitespace_content_counts_as_empty() -> None:
    assert classify_completion("   \n\t ", None, "stop") == CompletionOutcome.EMPTY


def test_tool_call_with_empty_content_is_usable() -> None:
    # A tool call legitimately has no prose and is never a filter.
    assert (
        classify_completion("", None, "content_filter", has_tool_calls=True)
        == CompletionOutcome.USABLE
    )


def test_outcome_value_is_audit_status_string() -> None:
    assert CompletionOutcome.FILTERED.value == "filtered"
    assert CompletionOutcome.EMPTY.value == "empty"
