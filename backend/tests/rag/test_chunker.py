"""Tests for RAG text chunker."""

from src.rag.chunker import chunk_text


class TestChunkText:
    def test_empty_text(self):
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_short_text_returns_as_is(self):
        text = "Short text."
        result = chunk_text(text, max_size=500)
        assert result == [text]

    def test_splits_by_paragraphs(self):
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        result = chunk_text(text, max_size=30, overlap=0)
        assert len(result) >= 2
        assert "First paragraph." in result[0]

    def test_splits_by_sentences(self):
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        result = chunk_text(text, max_size=35, overlap=0)
        assert len(result) >= 2

    def test_merges_small_chunks(self):
        text = "A.\n\nB.\n\nC."
        result = chunk_text(text, max_size=100, overlap=0)
        # All three are tiny — should merge into fewer chunks
        assert len(result) <= 2

    def test_overlap_prepends_previous_tail(self):
        text = "First chunk content here.\n\nSecond chunk content here."
        result = chunk_text(text, max_size=30, overlap=10)
        # Second chunk should start with tail of first
        if len(result) > 1:
            assert len(result[1]) > len("Second chunk content here.")

    def test_no_overlap(self):
        text = "Part one.\n\nPart two."
        result = chunk_text(text, max_size=15, overlap=0)
        assert len(result) >= 2
        # No overlap — chunks should not contain previous chunk's content
        if len(result) > 1:
            assert not result[1].startswith("Part one")

    def test_char_level_fallback(self):
        text = "A" * 100
        result = chunk_text(text, max_size=30, overlap=0)
        assert len(result) >= 3
        assert all(len(c) <= 30 for c in result)

    def test_custom_delimiters(self):
        text = "one|two|three"
        result = chunk_text(text, max_size=5, overlap=0, delimiters=["|"])
        assert "one" in result
        assert "two" in result
        assert "three" in result
