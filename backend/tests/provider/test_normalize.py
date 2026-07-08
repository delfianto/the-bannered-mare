"""Tests for tolerant model-output normalization."""

from src.provider.normalize import parse_structured_list, sanitize_narrative


class TestParseStructuredList:
    def test_plain_json(self):
        assert parse_structured_list('["a", "b", "c"]', 2) == ["a", "b"]

    def test_repairs_doubled_opening_quote(self):
        # Local models sometimes double the opening quote → invalid single-line
        # JSON. Must recover the individual items, not one "[...]" blob.
        raw = '[""Show me the dance.", "A little sugar sounds good.", "Tell me your secret."]'
        assert parse_structured_list(raw, 3) == [
            "Show me the dance.",
            "A little sugar sounds good.",
            "Tell me your secret.",
        ]

    def test_trailing_comma(self):
        assert parse_structured_list('["x", "y",]', 5) == ["x", "y"]

    def test_json_inside_markdown_fence(self):
        assert parse_structured_list('```json\n["one", "two"]\n```', 5) == ["one", "two"]

    def test_line_fallback(self):
        assert parse_structured_list("- first\n- second", 5) == ["first", "second"]

    def test_respects_count(self):
        assert parse_structured_list('["a","b","c","d"]', 2) == ["a", "b"]

    def test_never_leaks_brackets_or_quotes(self):
        for raw in ('[""x", "y"]', '["x","y",]', "- x\n- y", '["only"]'):
            items = parse_structured_list(raw, 5)
            assert items, raw
            assert all("[" not in i and "]" not in i and '"' not in i for i in items), raw


class TestSanitizeNarrative:
    def test_strips_gfx_block(self):
        raw = (
            "She smiles.\n\n<!-- GFX_START -->\n"
            '<div style="background:#fff">"Hello there."</div>\n<!-- GFX_END -->\n\n'
            "She waits."
        )
        out = sanitize_narrative(raw)
        assert "<div" not in out and "style=" not in out and "GFX" not in out
        assert '"Hello there."' in out
        assert "She smiles." in out and "She waits." in out

    def test_preserves_less_than_in_prose(self):
        assert sanitize_narrative("Only 5 < 10 guards remain.") == "Only 5 < 10 guards remain."

    def test_strips_inline_tags(self):
        assert sanitize_narrative("A <span class='x'>bold</span> move.") == "A bold move."

    def test_noop_on_clean_text(self):
        assert sanitize_narrative("Just plain narrative text.") == "Just plain narrative text."

    def test_quirk_hatch_inert_by_default(self):
        # An unregistered quirk flag never changes output (registry is empty).
        assert sanitize_narrative("<div>x</div>", quirks=("nonexistent",)) == "x"
