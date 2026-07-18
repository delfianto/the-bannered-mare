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
    # "ethnicity"/"nationality" are deliberately NOT species synonyms. There is no
    # ethnicity column on Character (core/persistence/models/character.py), and
    # real-world human cards routinely carry "Ethnicity: American" / "Nationality:
    # Korean" -- feeding those in only lands a nationality in `species`, which is
    # worse than leaving it blank. Only "race"/"species" (the fantasy/TTRPG sense)
    # map here; an occasional "Ethnicity: Elvish" is the rare miss we accept to
    # avoid corrupting the common human case.
    "species": re.compile(r"\b(?:race|species)\b\s*[:(]\s*\**\s*([^\n;)*]{1,30})", re.IGNORECASE),
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


# ---------------------------------------------------------------------------
# Prose-inferred fallback (lower confidence than a labeled field)
#
# Many cards never put species/age/gender in a `label:` field -- they state them
# in ordinary prose ("a mesmerizing Khajiit dancer", "a 24 year old woman", or
# just consistent she/her). These heuristics recover that, but ONLY for fields
# still blank after the extension + labeled-field passes, so a labeled value can
# never be overridden by a weaker prose guess. Kept deliberately conservative:
# leaving a field blank beats writing a wrong value into a filterable column.
# ---------------------------------------------------------------------------

# "24 year old", "24-year-old", "24yo", "aged 24". The number is captured from
# whichever alternative matched.
_AGE_PROSE_PATTERN = re.compile(
    r"\b(\d{1,3})[\s-]*(?:years?|yrs?)[\s-]*old\b"
    r"|\b(\d{1,3})\s*y[/.]?\s*o\b"
    r"|\baged\s+(\d{1,3})\b",
    re.IGNORECASE,
)

# Gendered pronouns/nouns that describe the character. Third-person cards state
# gender through these far more often than through a label. Pronouns dominate the
# signal; nouns disambiguate. {{user}} pronouns leak in (a female char with a
# male {{user}} still reads majority-female), so the tally requires a clear
# majority rather than a bare lead -- see _infer_gender_from_prose.
_FEMALE_TOKENS = re.compile(
    r"\b(?:she|her|hers|herself|woman|women|girl|girls|lady|ladies|gal|female|"
    r"mom|mother|sister|stepsister|daughter|aunt|niece|girlfriend|wife|widow|"
    r"queen|princess|goddess|actress|waitress)\b",
    re.IGNORECASE,
)
_MALE_TOKENS = re.compile(
    r"\b(?:he|him|his|himself|man|men|boy|boys|guy|guys|gentleman|male|"
    r"dad|father|brother|stepbrother|son|uncle|nephew|boyfriend|husband|widower|"
    r"king|prince|actor|waiter)\b",
    re.IGNORECASE,
)

# Curated race/species vocabulary for the prose fallback. Distinctive fantasy /
# supernatural / sci-fi races that are rarely metaphors; each maps its spelling
# variants to a canonical form. Figurative/complimentary words common in RP prose
# -- "angel", "demon", "goddess", "devil", "monster", "beast", "siren" -- are
# intentionally EXCLUDED so a human character described as "an angel" isn't stamped
# with a species. Extend as real cards require.
_SPECIES_VOCAB: dict[str, list[str]] = {
    "Human": ["humans?"],
    "Elf": ["elf", "elves", "elven", "elvish"],
    "Dwarf": ["dwarf", "dwarves", "dwarven"],
    "Orc": ["orc", "orcs", "orcish", "orsimer"],
    "Halfling": ["halfling", "halflings"],
    "Gnome": ["gnome", "gnomes"],
    "Tiefling": ["tiefling", "tieflings"],
    "Dragonborn": ["dragonborn"],
    "Drow": ["drow"],
    "Khajiit": ["khajiit"],
    "Argonian": ["argonian", "argonians"],
    "Nord": ["nord", "nords"],
    "Breton": ["breton", "bretons"],
    "Redguard": ["redguard", "redguards"],
    "Altmer": ["altmer", "high elf"],
    "Dunmer": ["dunmer", "dark elf"],
    "Bosmer": ["bosmer", "wood elf"],
    "Vampire": ["vampire", "vampires", "vampiric"],
    "Werewolf": ["werewolf", "werewolves", "lycan", "lycanthrope"],
    "Succubus": ["succubus", "succubi"],
    "Incubus": ["incubus", "incubi"],
    "Kitsune": ["kitsune"],
    "Neko": ["neko", "catgirl", "cat-girl", "nekomimi"],
    "Naga": ["naga"],
    "Lamia": ["lamia"],
    "Harpy": ["harpy", "harpies"],
    "Centaur": ["centaur", "centaurs"],
    "Mermaid": ["mermaid", "merfolk", "merman", "mermaid"],
    "Android": ["android", "androids"],
    "Cyborg": ["cyborg", "cyborgs"],
    "Robot": ["robot", "robots", "robotic"],
    "Elemental": ["elemental"],
}
_SPECIES_PROSE_PATTERNS = [
    (canonical, re.compile(r"\b(?:" + "|".join(variants) + r")\b", re.IGNORECASE))
    for canonical, variants in _SPECIES_VOCAB.items()
]


def _infer_age_from_prose(text: str) -> str:
    match = _AGE_PROSE_PATTERN.search(text)
    if not match:
        return ""
    return next(g for g in match.groups() if g)


def _infer_gender_from_prose(text: str) -> str:
    female = len(_FEMALE_TOKENS.findall(text))
    male = len(_MALE_TOKENS.findall(text))
    total = female + male
    if total < 2:  # too little signal to call
        return ""
    if female > male and female / total >= 0.6:
        return "Female"
    if male > female and male / total >= 0.6:
        return "Male"
    return ""


def _infer_species_from_prose(text: str) -> str:
    """Return the canonical species whose vocabulary term appears earliest in the
    text (a card names one species; earliest-wins keeps it deterministic)."""
    best_pos: int | None = None
    best_canonical = ""
    for canonical, pattern in _SPECIES_PROSE_PATTERNS:
        match = pattern.search(text)
        if match and (best_pos is None or match.start() < best_pos):
            best_pos = match.start()
            best_canonical = canonical
    return best_canonical


def fill_prose_inferred_attributes(card: ParsedCard) -> ParsedCard:
    """Second pass: infer species/age/gender from unlabeled prose, filling only
    fields still blank after ``fill_baked_in_attributes``. Never overrides a
    labeled or extension value -- prose is the lowest-confidence source.
    """
    haystack = "\n".join(filter(None, [card.description, card.personality]))
    if not haystack:
        return card
    if not card.age:
        card.age = _infer_age_from_prose(haystack)
    if not card.gender and not card.custom_gender:
        card.gender = _infer_gender_from_prose(haystack)
    if not card.species:
        card.species = _infer_species_from_prose(haystack)
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
    return fill_prose_inferred_attributes(fill_baked_in_attributes(normalize_card_quotes(card)))


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
