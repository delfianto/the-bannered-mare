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

import nh3

_ARRAY_RE = re.compile(r"\[[\s\S]*\]")
_QUOTED_RE = re.compile(r'"(.+?)"', re.DOTALL)
_TRAILING_COMMA_RE = re.compile(r",\s*]")
_LIST_MARKER_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s*")

_HTML_COMMENT_RE = re.compile(r"<!--[\s\S]*?-->")
# A tag must start with a letter (or /letter), so a stray "<" in "5 < 10" survives.
_HTML_TAG_RE = re.compile(r"<\/?[a-zA-Z][^>]*>")
_BLANK_RUN_RE = re.compile(r"\n{3,}")

# Typographic ("smart") quotes → ASCII. The frontend's dialogue detection keys on
# straight double quotes, so a curly-quoted reply would render entirely as
# narrative. Covers the Unicode single/double curly family plus the fullwidth
# forms some CJK-tuned local models emit. A str.translate table (codepoint →
# char) is a single pass with no regex; applied to the decoded str, so JSON
# serialization downstream escapes the introduced '"' as '\"' automatically.
_QUOTE_TRANSLATION = str.maketrans(
    {
        0x2018: "'",  # ‘ left single
        0x2019: "'",  # ’ right single / apostrophe
        0x201A: "'",  # ‚ low-9 single
        0x201B: "'",  # ‛ reversed single
        0x201C: '"',  # “ left double
        0x201D: '"',  # ” right double
        0x201E: '"',  # „ low-9 double
        0x201F: '"',  # ‟ reversed double
        0xFF07: "'",  # ＇ fullwidth apostrophe
        0xFF02: '"',  # ＂ fullwidth quotation mark
    }
)

# "Graphics" blocks some presets (e.g. SillyTavern's Freaky Frankenstein) instruct
# the model to emit: an inline-styled HTML card between GFX markers. These are
# intentional visuals, not leaked formatting — preserved (sanitized) rather than
# stripped, and the markers are kept so the frontend can render the block as HTML.
_GFX_BLOCK_RE = re.compile(r"<!--\s*GFX_START\s*-->([\s\S]*?)<!--\s*GFX_END\s*-->")

# Presentational allowlist for GFX HTML: structure + inline styling only. No
# links, media, or form elements, and only the style attribute — nh3 (ammonia)
# drops everything else, including any script/event-handler vector. The frontend
# sanitizes again with DOMPurify before injecting (defense in depth).
_GFX_ALLOWED_TAGS = {"div", "span", "p", "br", "hr", "b", "strong", "i", "em", "u", "s", "small"}
_GFX_ALLOWED_ATTRIBUTES = {"*": {"style"}}


def normalize_quotes(text: str) -> str:
    """Replace typographic single/double quotes with their ASCII equivalents."""
    return text.translate(_QUOTE_TRANSLATION)


def parse_structured_list(raw: str, count: int) -> list[str]:
    """Parse a model's "JSON array of strings" into clean items, tolerantly.

    Handles the common local-model malformations: a doubled opening quote
    (``[""a", "b"]``), a trailing comma, curly quotes used as the string
    delimiters, or the whole array on one line. Order: strict JSON -> light
    repair (collapse doubled quotes, drop trailing commas, then the same with
    quotes ASCII-fied) -> extract the quoted segments directly -> one item per
    line. Items never retain the array brackets or quotes, and always come out
    with ASCII quotes.
    """
    text = raw.strip()
    match = _ARRAY_RE.search(text)
    if match:
        blob = match.group(0)
        # Strict first (never mangle valid JSON), then repaired variants. Quote
        # translation is a *repair*, not a pre-pass: a curly quote inside a
        # validly delimited string would become '"' and break the parse.
        repaired = _TRAILING_COMMA_RE.sub("]", blob.replace('""', '"'))
        for candidate in (blob, repaired, normalize_quotes(blob), normalize_quotes(repaired)):
            try:
                data = json.loads(candidate)
            except json.JSONDecodeError, ValueError:
                continue
            if isinstance(data, list):
                items = [normalize_quotes(str(x).strip()) for x in data if str(x).strip()]
                if items:
                    return items[:count]
        # Still unparseable — pull the quoted segments out so a malformed blob
        # never leaks through as one giant "[...]" item.
        quoted = [q.strip().strip('"').strip() for q in _QUOTED_RE.findall(normalize_quotes(blob))]
        quoted = [q for q in quoted if q]
        if quoted:
            return quoted[:count]

    items: list[str] = []
    for raw_line in normalize_quotes(text).splitlines():
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


def _sanitize_gfx(fragment: str) -> str:
    """Sanitize one GFX block's inner HTML against the presentational allowlist."""
    return nh3.clean(fragment, tags=_GFX_ALLOWED_TAGS, attributes=_GFX_ALLOWED_ATTRIBUTES).strip()


def _sanitize_prose(segment: str, quirks: Sequence[str]) -> str:
    """Clean a narrative (non-GFX) segment: drop comments/tags, ASCII quotes."""
    text = _HTML_COMMENT_RE.sub("", segment)
    text = _HTML_TAG_RE.sub("", text)
    text = normalize_quotes(text)
    for flag in quirks:
        handler = _QUIRK_HANDLERS.get(flag)
        if handler:
            text = handler(text)
    return text


def sanitize_narrative(raw: str, quirks: Sequence[str] = ()) -> str:
    """Normalize model output into clean narrative prose plus intact GFX blocks.

    Complete ``<!-- GFX_START -->…<!-- GFX_END -->`` blocks are intentional
    visuals: their inner HTML is sanitized (allowlist: layout tags + ``style``)
    and kept between the markers for the frontend to render. Everything outside
    them is prose — HTML comments and stray tags are removed (a tag must start
    with a letter, so a legitimate ``<`` in "5 < 10" survives), and typographic
    quotes become ASCII so dialogue detection keys on ``"…"`` reliably. Quotes
    inside GFX HTML are left alone — translating them there could corrupt
    attribute values. ``quirks`` applies any per-family handlers registered in
    ``_QUIRK_HANDLERS`` to the prose segments.
    """
    parts: list[str] = []
    last = 0
    for match in _GFX_BLOCK_RE.finditer(raw):
        parts.append(_sanitize_prose(raw[last : match.start()], quirks))
        gfx = _sanitize_gfx(match.group(1))
        if gfx:
            parts.append(f"\n\n<!-- GFX_START -->\n{gfx}\n<!-- GFX_END -->\n\n")
        last = match.end()
    parts.append(_sanitize_prose(raw[last:], quirks))
    return _BLANK_RUN_RE.sub("\n\n", "".join(parts)).strip()
