"""Tests for reasoning tag parsing utility."""

from src.core.utils.reasoning import parse_reasoning_tags


class TestParseReasoningTags:
    def test_no_tags_returns_original(self):
        content, reasoning = parse_reasoning_tags("Hello world")
        assert content == "Hello world"
        assert reasoning is None

    def test_empty_string(self):
        content, reasoning = parse_reasoning_tags("")
        assert content == ""
        assert reasoning is None

    def test_basic_think_tags(self):
        text = "<think>Let me consider this...</think>The answer is 42."
        content, reasoning = parse_reasoning_tags(text)
        assert content == "The answer is 42."
        assert reasoning == "Let me consider this..."

    def test_multiline_thinking(self):
        text = (
            "<think>\nStep 1: Consider the question.\n"
            "Step 2: Form an answer.\n</think>\n"
            '*Alice nods thoughtfully.* "Indeed."'
        )
        content, reasoning = parse_reasoning_tags(text)
        assert "Step 1" in reasoning
        assert "Step 2" in reasoning
        assert "*Alice nods thoughtfully.*" in content

    def test_unclosed_tag_treats_rest_as_reasoning(self):
        text = "<think>Still thinking about this..."
        content, reasoning = parse_reasoning_tags(text)
        assert content == ""
        assert reasoning == "Still thinking about this..."

    def test_multiple_think_blocks(self):
        text = (
            "<think>First thought</think>Response one. <think>Second thought</think>Response two."
        )
        content, reasoning = parse_reasoning_tags(text)
        assert "First thought" in reasoning
        assert "Second thought" in reasoning
        assert "Response one." in content
        assert "Response two." in content

    def test_custom_prefix_suffix(self):
        text = "[reasoning]My analysis[/reasoning]Here is the result."
        content, reasoning = parse_reasoning_tags(text, prefix="[reasoning]", suffix="[/reasoning]")
        assert content == "Here is the result."
        assert reasoning == "My analysis"

    def test_content_before_and_after(self):
        text = "Preamble. <think>Internal monologue</think>Actual response."
        content, reasoning = parse_reasoning_tags(text)
        assert "Preamble." in content
        assert "Actual response." in content
        assert reasoning == "Internal monologue"

    def test_only_think_tags_no_content(self):
        text = "<think>Just reasoning, no response</think>"
        content, reasoning = parse_reasoning_tags(text)
        assert content == ""
        assert reasoning == "Just reasoning, no response"

    def test_whitespace_handling(self):
        text = "  <think>  padded reasoning  </think>  padded content  "
        content, reasoning = parse_reasoning_tags(text)
        assert reasoning == "padded reasoning"
        assert content == "padded content"
