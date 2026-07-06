"""TavernCard V1/V2 character card parser and exporter.

Handles:
- PNG files with base64-encoded JSON in tEXt chunk (keyword: 'chara')
- Plain JSON files (V1 or V2 format)
- Export to PNG (embed JSON in tEXt chunk) and JSON
"""

import base64
import io
import json
import struct
import zlib
from dataclasses import dataclass, field
from typing import Any

from PIL import Image


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

    Detects V1 vs V2 automatically based on the presence of 'spec' and 'data' keys.
    """
    data = json.loads(raw_json) if isinstance(raw_json, str) else raw_json

    if "spec" in data and "data" in data:
        return _parse_v2_data(data["data"])

    if "data" in data and isinstance(data["data"], dict):
        return _parse_v2_data(data["data"])

    return _parse_v1_data(data)


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
