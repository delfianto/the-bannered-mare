"""Tests for tolerant model-output normalization."""

from src.chat_message.normalize import normalize_quotes, parse_structured_list, sanitize_narrative


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

    def test_repairs_curly_quoted_json(self):
        # Some local models emit the array with curly quotes as delimiters.
        raw = "[“Show me.”, “Tell me more.”]"
        assert parse_structured_list(raw, 3) == ["Show me.", "Tell me more."]

    def test_valid_json_with_inner_curly_quotes_survives(self):
        # Strict parse must win before quote repair: translating the inner
        # curly quotes first would unterminate the string.
        raw = '["She said “stay” softly", "ok"]'
        assert parse_structured_list(raw, 3) == ['She said "stay" softly', "ok"]

    def test_never_leaks_brackets_or_quotes(self):
        for raw in ('[""x", "y"]', '["x","y",]', "- x\n- y", '["only"]'):
            items = parse_structured_list(raw, 5)
            assert items, raw
            assert all("[" not in i and "]" not in i and '"' not in i for i in items), raw


class TestNormalizeQuotes:
    def test_curly_family(self):
        assert normalize_quotes("“Who said you could—”") == '"Who said you could—"'
        assert normalize_quotes("Mina’s phone") == "Mina's phone"
        assert normalize_quotes("„ja“ ‚so‘") == "\"ja\" 'so'"

    def test_fullwidth(self):
        assert normalize_quotes("＂hai＂ ＇ok＇") == "\"hai\" 'ok'"

    def test_ascii_untouched(self):
        assert normalize_quotes('"Stay." It\'s fine.') == '"Stay." It\'s fine.'


class TestSanitizeNarrative:
    def test_normalizes_smart_quotes_in_prose(self):
        raw = "She shoves at your shoulder. “Who said you could—” Her protest cuts."
        out = sanitize_narrative(raw)
        assert "“" not in out and "”" not in out
        assert '"Who said you could—"' in out

    def test_preserves_gfx_block_sanitized(self):
        raw = (
            "She smiles.\n\n<!-- GFX_START -->\n"
            '<div style="background:#000"><span style="color:#aaa">4:12 PM</span>'
            "<script>alert(1)</script>"
            '<a href="https://evil.example">x</a></div>\n<!-- GFX_END -->\n\n'
            "She waits."
        )
        out = sanitize_narrative(raw)
        assert "<!-- GFX_START -->" in out and "<!-- GFX_END -->" in out
        assert '<div style="background:#000">' in out
        assert '<span style="color:#aaa">4:12 PM</span>' in out
        assert "<script" not in out and "alert(1)" not in out
        assert "<a" not in out and "href" not in out
        assert "She smiles." in out and "She waits." in out

    def test_gfx_keeps_smart_quotes_prose_does_not(self):
        # Quote translation inside GFX HTML could corrupt attribute values, so
        # only the prose around the block is normalized.
        raw = (
            "“Send it.”\n\n<!-- GFX_START -->"
            "<div>Saving to “proof \U0001f602”</div>"
            "<!-- GFX_END -->"
        )
        out = sanitize_narrative(raw)
        assert '"Send it."' in out
        assert "Saving to “proof \U0001f602”" in out

    def test_unterminated_gfx_degrades_to_stripped_text(self):
        raw = 'Text.\n\n<!-- GFX_START -->\n<div style="x">00:23</div>'
        out = sanitize_narrative(raw)
        assert "GFX" not in out and "<div" not in out
        assert "Text." in out and "00:23" in out

    def test_strips_non_gfx_html_comments_and_tags(self):
        raw = "She smiles. <!-- note --><b>loudly</b>"
        assert sanitize_narrative(raw) == "She smiles. loudly"

    def test_preserves_less_than_in_prose(self):
        assert sanitize_narrative("Only 5 < 10 guards remain.") == "Only 5 < 10 guards remain."

    def test_strips_inline_tags(self):
        assert sanitize_narrative("A <span class='x'>bold</span> move.") == "A bold move."

    def test_noop_on_clean_text(self):
        assert sanitize_narrative("Just plain narrative text.") == "Just plain narrative text."

    def test_quirk_hatch_inert_by_default(self):
        # An unregistered quirk flag never changes output (registry is empty).
        assert sanitize_narrative("<div>x</div>", quirks=("nonexistent",)) == "x"
