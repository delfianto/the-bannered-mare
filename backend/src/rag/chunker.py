"""Recursive delimiter-based text splitter for RAG chunking."""

DEFAULT_DELIMITERS = ["\n\n", "\n", ". ", " "]


def chunk_text(
    text: str,
    max_size: int = 500,
    overlap: int = 50,
    delimiters: list[str] | None = None,
) -> list[str]:
    """Recursive delimiter-based text splitter.

    Splits by paragraphs, sentences, words, then chars.
    Merges short chunks and prepends overlap from previous chunk.
    """
    if not text or not text.strip():
        return []

    if len(text) <= max_size:
        return [text]

    if delimiters is None:
        delimiters = DEFAULT_DELIMITERS

    chunks = _split_recursive(text, max_size, delimiters)
    chunks = _merge_small_chunks(chunks, max_size)
    chunks = _apply_overlap(chunks, overlap)
    return chunks


def _split_recursive(text: str, max_size: int, delimiters: list[str]) -> list[str]:
    """Split text using the first delimiter that produces sub-max_size pieces,
    falling back to subsequent delimiters for oversized pieces."""
    if len(text) <= max_size:
        return [text]

    if not delimiters:
        return _split_by_chars(text, max_size)

    delimiter = delimiters[0]
    remaining_delimiters = delimiters[1:]

    parts = text.split(delimiter)
    parts = [p for p in parts if p.strip()]

    if len(parts) <= 1:
        return _split_recursive(text, max_size, remaining_delimiters)

    result: list[str] = []
    for part in parts:
        if len(part) <= max_size:
            result.append(part)
        else:
            result.extend(_split_recursive(part, max_size, remaining_delimiters))

    return result


def _split_by_chars(text: str, max_size: int) -> list[str]:
    """Last-resort character-level splitting."""
    return [text[i : i + max_size] for i in range(0, len(text), max_size)]


def _merge_small_chunks(chunks: list[str], max_size: int) -> list[str]:
    """Merge adjacent chunks that together fit within max_size."""
    if not chunks:
        return []

    merged: list[str] = [chunks[0]]
    for chunk in chunks[1:]:
        combined = merged[-1] + " " + chunk
        if len(combined) <= max_size:
            merged[-1] = combined
        else:
            merged.append(chunk)

    return merged


def _apply_overlap(chunks: list[str], overlap: int) -> list[str]:
    """Prepend the tail of the previous chunk to the current chunk for context."""
    if overlap <= 0 or len(chunks) <= 1:
        return chunks

    result = [chunks[0]]
    for i in range(1, len(chunks)):
        prev_tail = chunks[i - 1][-overlap:]
        result.append(prev_tail + chunks[i])

    return result
