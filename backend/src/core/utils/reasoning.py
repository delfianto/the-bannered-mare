"""Utilities for extracting reasoning/thinking content from model output."""

_DEFAULT_PREFIX = "<think>"
_DEFAULT_SUFFIX = "</think>"


def parse_reasoning_tags(
    text: str,
    prefix: str = _DEFAULT_PREFIX,
    suffix: str = _DEFAULT_SUFFIX,
) -> tuple[str, str | None]:
    """Extract reasoning from text that uses think tags (e.g. <think>...</think>).

    Common in local models like DeepSeek R1, QwQ, Qwen3 that embed reasoning
    directly in output rather than using a separate API field.

    Args:
        text: Raw model output potentially containing think tags.
        prefix: Opening tag (default: "<think>").
        suffix: Closing tag (default: "</think>").

    Returns:
        Tuple of (clean_content, reasoning_or_none).
        If no tags found, returns (original_text, None).
    """
    if not text or prefix not in text:
        return text, None

    reasoning_parts: list[str] = []
    content_parts: list[str] = []
    remaining = text

    while prefix in remaining:
        before, _, after_prefix = remaining.partition(prefix)
        if before.strip():
            content_parts.append(before.strip())

        if suffix in after_prefix:
            reasoning_block, _, after_suffix = after_prefix.partition(suffix)
            reasoning_parts.append(reasoning_block.strip())
            remaining = after_suffix
        else:
            # Unclosed tag — treat rest as reasoning
            reasoning_parts.append(after_prefix.strip())
            remaining = ""
            break

    if remaining.strip():
        content_parts.append(remaining.strip())

    reasoning = "\n\n".join(reasoning_parts) if reasoning_parts else None
    content = "\n\n".join(content_parts) if content_parts else ""

    return content, reasoning
