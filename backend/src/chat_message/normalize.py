"""Tolerant normalization of raw model output.

The boundary between what a model is *asked* to return and what it *actually*
returns. Local and quantized models routinely deviate — malformed JSON (a doubled
opening quote, a trailing comma), or raw HTML "graphics" blocks injected into
narrative prose. Per Postel's law we are strict in what we request (the
prompt/schema) and tolerant in what we accept, so every consumer downstream of
this module sees clean data.

Scope: this handles the *stochastic* format sloppiness that any model can emit
unpredictably, applied universally. The *deterministic*, per-family capability
quirks (which sampling params a model rejects, which reasoning control it uses)
are not here — they live in the model-family catalog (``unsupported_parameters``
plus the per-provider adapter maps), keyed by family identity.
"""

import json
import re
from collections.abc import Callable, Sequence

_ARRAY_RE = re.compile(r"\[[\s\S]*\]")
_QUOTED_RE = re.compile(r'"(.+?)"', re.DOTALL)
_TRAILING_COMMA_RE = re.compile(r",\s*]")
_LIST_MARKER_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s*")

_HTML_COMMENT_RE = re.compile(r"<!--[\s\S]*?-->")
# A tag must start with a letter (or /letter), so a stray "<" in "5 < 10" survives.
_HTML_TAG_RE = re.compile(r"<\/?[a-zA-Z][^>]*>")
_BLANK_RUN_RE = re.compile(r"\n{3,}")


def parse_structured_list(raw: str, count: int) -> list[str]:
    """Parse a model's "JSON array of strings" into clean items, tolerantly.

    Handles the common local-model malformations: a doubled opening quote
    (``[""a", "b"]``), a trailing comma, or the whole array on one line. Order:
    strict JSON -> light repair (collapse doubled quotes, drop trailing commas)
    -> extract the quoted segments directly -> one item per line. Items never
    retain the array brackets or quotes.
    """
    text = raw.strip()
    match = _ARRAY_RE.search(text)
    if match:
        blob = match.group(0)
        # Strict first (never mangle valid JSON), then a repaired variant.
        repaired = _TRAILING_COMMA_RE.sub("]", blob.replace('""', '"'))
        for candidate in (blob, repaired):
            try:
                data = json.loads(candidate)
            except json.JSONDecodeError, ValueError:
                continue
            if isinstance(data, list):
                items = [str(x).strip() for x in data if str(x).strip()]
                if items:
                    return items[:count]
        # Still unparseable — pull the quoted segments out so a malformed blob
        # never leaks through as one giant "[...]" item.
        quoted = [q.strip().strip('"').strip() for q in _QUOTED_RE.findall(blob)]
        quoted = [q for q in quoted if q]
        if quoted:
            return quoted[:count]

    items: list[str] = []
    for raw_line in text.splitlines():
        line = _LIST_MARKER_RE.sub("", raw_line.strip())
        line = line.strip().strip("[]").strip().strip('"').strip()
        if line:
            items.append(line)
    return items[:count]


# Per-family narrative quirk handlers — the escape hatch for a cleanup too
# model-specific to apply universally. Keyed by a flag a family carries in
# ``extra_metadata["quirks"]``; intentionally empty until something needs it.
# To add one: register {flag: fn} here and pass the family's quirks into
# ``sanitize_narrative`` at the call site.
_QUIRK_HANDLERS: dict[str, Callable[[str], str]] = {}


def sanitize_narrative(raw: str, quirks: Sequence[str] = ()) -> str:
    """Strip formatting a model leaked into narrative prose.

    Always removes HTML comments and HTML tags — e.g. the ``<!-- GFX_START -->``
    ``<div style="…">…</div>`` "graphics" blocks some uncensored finetunes emit,
    which would otherwise render as literal tags. A tag must start with a letter,
    so a legitimate ``<`` (e.g. "5 < 10") is preserved. ``quirks`` applies any
    per-family handlers registered in ``_QUIRK_HANDLERS``.
    """
    text = _HTML_COMMENT_RE.sub("", raw)
    text = _HTML_TAG_RE.sub("", text)
    for flag in quirks:
        handler = _QUIRK_HANDLERS.get(flag)
        if handler:
            text = handler(text)
    return _BLANK_RUN_RE.sub("\n\n", text).strip()
