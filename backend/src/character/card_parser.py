"""TavernCard V1/V2 character card parser and exporter.

Handles:
- PNG files with base64-encoded JSON in tEXt chunk (keyword: 'chara')
- Plain JSON files (V1 or V2 format)
- Export to PNG (embed JSON in tEXt chunk) and JSON
"""

import base64
import io
import json
import re
import struct
import zlib
from dataclasses import dataclass, field, fields
from typing import Any

from PIL import Image

# Card creators mix typewriter tools (straight quotes) and rich editors like Word/
# Google Docs (auto-curled quotes) -- often within the same field of the same card
# -- so imported text ends up with both conventions for what should read as one
# character. Folding to ASCII keeps exact-match consumers (lore keyword triggers,
# search) from missing a hit because of a typographic quote mismatch.
_SMART_QUOTE_TRANSLATION = str.maketrans(
    {
        "‘": "'",  # left single quotation mark
        "’": "'",  # right single quotation mark
        "“": '"',  # left double quotation mark
        "”": '"',  # right double quotation mark
    }
)


def normalize_smart_quotes(text: str) -> str:
    """Fold Unicode "smart" quotes to their ASCII equivalents."""
    return text.translate(_SMART_QUOTE_TRANSLATION)


def normalize_card_quotes(card: ParsedCard) -> ParsedCard:
    """Apply ``normalize_smart_quotes`` to every string/string-list field on a card.

    ``extensions`` and ``character_book`` are left untouched -- they're structured
    data (and the lore domain owns normalizing ``character_book`` prose if needed).
    """
    for f in fields(card):
        value = getattr(card, f.name)
        if isinstance(value, str):
            setattr(card, f.name, normalize_smart_quotes(value))
        elif isinstance(value, list) and value and isinstance(value[0], str):
            setattr(card, f.name, [normalize_smart_quotes(v) for v in value])
    return card


# Most cards leave species/gender/age unset (the bannered_mare extension is our
# own invention -- essentially nobody in the wider card ecosystem uses it) but
# often bake them into description/personality as an informal "character sheet":
# "**Age:** 19", "🎂 Age: 20", "{{char}} sex(Female)". Anchored to an explicit
# label immediately followed by `:` or `(` -- deliberately does NOT try to infer
# from unlabeled prose ("a mesmerizing Khajiit dancer"), since a wrong guess
# writes bad data into a filterable field, which is worse than leaving it blank.
_ATTR_LABEL_PATTERNS = {
    "age": re.compile(r"\bage\b\s*[:(]\s*\**\s*([^\n;)*]{1,20})", re.IGNORECASE),
    "gender": re.compile(r"\b(?:sex|gender)\b\s*[:(]\s*\**\s*([^\n;)*]{1,20})", re.IGNORECASE),
    "species": re.compile(
        r"\b(?:race|species|ethnicity)\b\s*[:(]\s*\**\s*([^\n;)*]{1,30})", re.IGNORECASE
    ),
}


def _extract_labeled_attribute(text: str, pattern: re.Pattern[str]) -> str:
    match = pattern.search(text)
    return match.group(1).strip(" .,;*") if match else ""


def fill_baked_in_attributes(card: ParsedCard) -> ParsedCard:
    """Fill species/gender/age from an explicit label in description/personality,
    but only where the card's own (higher-confidence) extension fields left them
    blank -- extension data always wins over text extraction.
    """
    haystack = "\n".join(filter(None, [card.description, card.personality]))
    if not haystack:
        return card
    if not card.age:
        card.age = _extract_labeled_attribute(haystack, _ATTR_LABEL_PATTERNS["age"])
    if not card.gender and not card.custom_gender:
        card.gender = _extract_labeled_attribute(haystack, _ATTR_LABEL_PATTERNS["gender"])
    if not card.species:
        card.species = _extract_labeled_attribute(haystack, _ATTR_LABEL_PATTERNS["species"])
    return card


def split_example_dialogues(mes_example: str) -> list[str]:
    """Split a TavernCard ``mes_example`` string into individual example blocks.

    Cards store example chats as one freeform string with each example delimited
    by a ``<START>`` marker (SillyTavern convention). We return one entry per
    non-empty block with the marker stripped; a card with no markers becomes a
    single block, and empty/whitespace-only blocks (e.g. a bare ``<START>``
    template) are dropped so they don't become bogus example dialogues.
    """
    if not mes_example or not mes_example.strip():
        return []
    parts = re.split(r"<START>", mes_example, flags=re.IGNORECASE)
    return [block for part in parts if (block := part.strip())]


@dataclass
class ParsedCard:
    """Normalized character card data from any supported format."""

    name: str
    description: str = ""
    personality: str = ""
    first_message: str = ""
    example_dialogues: str = ""
    scenario: str = ""
    system_prompt: str = ""
    post_history_instructions: str = ""
    creator_notes: str = ""
    creator: str = ""
    character_version: str = ""
    alternate_greetings: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    extensions: dict[str, Any] = field(default_factory=dict)
    character_book: dict[str, Any] = field(default_factory=dict)
    species: str = ""
    gender: str = ""
    custom_gender: str = ""
    age: str = ""
    spec: str = "chara_card_v2"
    spec_version: str = "2.0"


def _read_png_text_chunks(data: bytes) -> dict[str, str]:
    """Extract tEXt chunks from raw PNG bytes."""
    chunks: dict[str, str] = {}
    buf = io.BytesIO(data)

    sig = buf.read(8)
    if sig != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a valid PNG file")

    while True:
        raw = buf.read(8)
        if len(raw) < 8:
            break
        length, chunk_type = struct.unpack(">I4s", raw)
        chunk_data = buf.read(length)
        buf.read(4)  # CRC

        ct = chunk_type.decode("latin-1")
        if ct == "tEXt":
            null_idx = chunk_data.index(b"\x00")
            keyword = chunk_data[:null_idx].decode("latin-1")
            value = chunk_data[null_idx + 1 :].decode("latin-1")
            chunks[keyword] = value
        elif ct == "IEND":
            break

    return chunks


def _parse_v2_data(data: dict[str, Any]) -> ParsedCard:
    """Parse V2 'data' object into a ParsedCard."""
    exts = data.get("extensions", {})
    ck_ext = exts.get("bannered_mare", {})
    cp_ext = exts.get("chara_personal_details", {})

    species = ck_ext.get("species") or exts.get("species") or cp_ext.get("species") or ""
    age = ck_ext.get("age") or exts.get("age") or cp_ext.get("age") or ""
    gender = ck_ext.get("gender") or exts.get("gender") or cp_ext.get("gender") or ""
    custom_gender = ck_ext.get("custom_gender") or exts.get("custom_gender") or ""

    return ParsedCard(
        name=data.get("name", "Unknown"),
        description=data.get("description", ""),
        personality=data.get("personality", ""),
        first_message=data.get("first_mes", ""),
        example_dialogues=data.get("mes_example", ""),
        scenario=data.get("scenario", ""),
        system_prompt=data.get("system_prompt", ""),
        post_history_instructions=data.get("post_history_instructions", ""),
        creator_notes=data.get("creator_notes", ""),
        creator=data.get("creator", ""),
        character_version=data.get("character_version", ""),
        alternate_greetings=data.get("alternate_greetings", []),
        tags=data.get("tags", []),
        extensions=exts,
        character_book=data.get("character_book", {}),
        species=str(species),
        gender=str(gender),
        custom_gender=str(custom_gender),
        age=str(age),
        spec=data.get("spec", "chara_card_v2"),
        spec_version=data.get("spec_version", "2.0"),
    )


def _parse_v1_data(data: dict[str, Any]) -> ParsedCard:
    """Parse V1 flat JSON into a ParsedCard."""
    return ParsedCard(
        name=data.get("name") or data.get("char_name", "Unknown"),
        description=data.get("description") or data.get("char_persona", ""),
        personality=data.get("personality", ""),
        first_message=data.get("first_mes") or data.get("char_greeting", ""),
        example_dialogues=data.get("mes_example") or data.get("example_dialogue", ""),
        scenario=data.get("scenario") or data.get("world_scenario", ""),
        spec="chara_card_v1",
        spec_version="1.0",
    )


def parse_card_json(raw_json: str | dict[str, Any]) -> ParsedCard:
    """
    Parse a character card from JSON (string or dict).

    Detects V1 vs V2 automatically: a dict ``data`` key marks a V2 card (the
    ``spec`` key is advisory, not required), otherwise the payload is flat V1.
    """
    data = json.loads(raw_json) if isinstance(raw_json, str) else raw_json

    card = (
        _parse_v2_data(data["data"])
        if "data" in data and isinstance(data["data"], dict)
        else _parse_v1_data(data)
    )
    return fill_baked_in_attributes(normalize_card_quotes(card))


def parse_card_png(png_data: bytes) -> ParsedCard:
    """
    Extract and parse a character card from PNG tEXt chunk.

    Reads the 'chara' keyword from tEXt chunks, base64-decodes it, and parses the JSON.
    """
    chunks = _read_png_text_chunks(png_data)

    if "chara" not in chunks:
        raise ValueError("PNG does not contain a character card (no 'chara' tEXt chunk)")

    decoded = base64.b64decode(chunks["chara"]).decode("utf-8")
    return parse_card_json(decoded)


def card_to_v2_dict(card: ParsedCard) -> dict[str, Any]:
    """Convert a ParsedCard back to TavernCard V2 JSON structure."""
    extensions = dict(card.extensions or {})

    ck_data = {}
    if card.species:
        ck_data["species"] = card.species
        extensions["species"] = card.species
    if card.gender:
        ck_data["gender"] = card.gender
        extensions["gender"] = card.gender
    if card.custom_gender:
        ck_data["custom_gender"] = card.custom_gender
        extensions["custom_gender"] = card.custom_gender
    if card.age:
        ck_data["age"] = card.age
        extensions["age"] = card.age

    if ck_data:
        extensions["bannered_mare"] = ck_data

    res = {
        "spec": "chara_card_v2",
        "spec_version": "2.0",
        "data": {
            "name": card.name,
            "description": card.description,
            "personality": card.personality,
            "first_mes": card.first_message,
            "mes_example": card.example_dialogues,
            "scenario": card.scenario,
            "system_prompt": card.system_prompt,
            "post_history_instructions": card.post_history_instructions,
            "creator_notes": card.creator_notes,
            "creator": card.creator,
            "character_version": card.character_version,
            "alternate_greetings": card.alternate_greetings,
            "tags": card.tags,
            "extensions": extensions,
        },
    }
    if card.character_book:
        res["data"]["character_book"] = card.character_book
    return res


def export_card_png(card: ParsedCard, avatar_data: bytes | None = None) -> bytes:
    """
    Export a character card as a PNG with embedded V2 JSON in tEXt chunk.

    If avatar_data is provided, it's used as the base image.
    Otherwise, a 1x1 transparent placeholder PNG is generated.
    """
    if avatar_data:
        img = Image.open(io.BytesIO(avatar_data))
    else:
        img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))

    img = img.convert("RGBA")

    v2_json = json.dumps(card_to_v2_dict(card), ensure_ascii=False)
    encoded = base64.b64encode(v2_json.encode("utf-8")).decode("ascii")

    # Save PNG to buffer
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    # Inject tEXt chunk before IEND
    text_chunk = _build_text_chunk("chara", encoded)

    iend_pos = png_bytes.rfind(b"IEND") - 4  # 4 bytes for length field
    return png_bytes[:iend_pos] + text_chunk + png_bytes[iend_pos:]


def export_card_json(card: ParsedCard) -> str:
    """Export a character card as a V2 JSON string."""
    return json.dumps(card_to_v2_dict(card), indent=2, ensure_ascii=False)


def _build_text_chunk(keyword: str, value: str) -> bytes:
    """Build a PNG tEXt chunk with the given keyword and value."""
    payload = keyword.encode("latin-1") + b"\x00" + value.encode("latin-1")
    chunk_type = b"tEXt"
    length = struct.pack(">I", len(payload))
    crc = struct.pack(">I", zlib.crc32(chunk_type + payload) & 0xFFFFFFFF)
    return length + chunk_type + payload + crc
