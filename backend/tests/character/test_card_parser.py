"""Tests for character card parser — V1/V2 PNG and JSON import/export."""

import json
from pathlib import Path

import pytest
from src.character.card_parser import (
    ParsedCard,
    card_to_v2_dict,
    export_card_json,
    export_card_png,
    parse_card_json,
    parse_card_png,
)

HOMEROOM_PNG = Path(__file__).parent.parent / "data" / "homeroom.png"


class TestParseCardJson:
    def test_parse_v2_card(self):
        v2 = {
            "spec": "chara_card_v2",
            "spec_version": "2.0",
            "data": {
                "name": "Alice",
                "description": "A curious girl",
                "personality": "Adventurous",
                "first_mes": "Hello there!",
                "mes_example": "<START>{{user}}: Hi\n{{char}}: Hello!",
                "scenario": "In a tea party",
                "system_prompt": "You are Alice.",
                "post_history_instructions": "Stay in character.",
                "creator_notes": "Based on Lewis Carroll",
                "creator": "test_author",
                "character_version": "1.0.0",
                "alternate_greetings": ["Hey!", "Good day!"],
                "tags": ["fantasy", "classic"],
            },
        }
        card = parse_card_json(v2)

        assert card.name == "Alice"
        assert card.description == "A curious girl"
        assert card.first_message == "Hello there!"
        assert card.system_prompt == "You are Alice."
        assert card.creator == "test_author"
        assert card.character_version == "1.0.0"
        assert len(card.alternate_greetings) == 2
        assert "fantasy" in card.tags

    def test_parse_v1_card(self):
        v1 = {
            "name": "Bob",
            "description": "A friendly bot",
            "personality": "Helpful",
            "first_mes": "Hi!",
            "mes_example": "Example dialogue",
            "scenario": "Office setting",
        }
        card = parse_card_json(v1)

        assert card.name == "Bob"
        assert card.first_message == "Hi!"
        assert card.spec == "chara_card_v1"
        assert card.system_prompt == ""

    def test_parse_v1_alt_field_names(self):
        v1_alt = {
            "char_name": "Charlie",
            "char_persona": "A detective",
            "char_greeting": "Welcome.",
            "example_dialogue": "Some dialogue",
            "world_scenario": "1920s London",
        }
        card = parse_card_json(v1_alt)

        assert card.name == "Charlie"
        assert card.description == "A detective"
        assert card.first_message == "Welcome."

    def test_parse_from_json_string(self):
        card = parse_card_json('{"name": "Direct", "description": "From string"}')
        assert card.name == "Direct"


class TestParseCardPng:
    @pytest.mark.skipif(not HOMEROOM_PNG.exists(), reason="Test PNG not available")
    def test_parse_homeroom_png(self):
        """Integration test with real character card PNG."""
        card = parse_card_png(HOMEROOM_PNG.read_bytes())

        assert card.name == "Your Young Homeroom Teacher"
        assert len(card.description) > 0
        assert len(card.first_message) > 0
        assert card.spec == "chara_card_v2"

    def test_invalid_png_raises(self):
        with pytest.raises(ValueError, match="Not a valid PNG"):
            parse_card_png(b"not a png file")

    def test_png_without_chara_chunk_raises(self):
        import io

        from PIL import Image

        img = Image.new("RGBA", (10, 10), (255, 0, 0, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        with pytest.raises(ValueError, match="no 'chara' tEXt chunk"):
            parse_card_png(buf.getvalue())


class TestExport:
    def test_export_json_roundtrip(self):
        card = ParsedCard(
            name="Test",
            description="A test character",
            first_message="Hello!",
            creator="tester",
        )
        json_str = export_card_json(card)
        parsed = json.loads(json_str)

        assert parsed["spec"] == "chara_card_v2"
        assert parsed["data"]["name"] == "Test"
        assert parsed["data"]["first_mes"] == "Hello!"

    def test_export_png_roundtrip(self):
        card = ParsedCard(
            name="PngTest",
            description="Exported to PNG",
            first_message="Greetings!",
        )
        png_bytes = export_card_png(card)

        # Verify it's valid PNG
        assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"

        # Parse it back
        reimported = parse_card_png(png_bytes)
        assert reimported.name == "PngTest"
        assert reimported.first_message == "Greetings!"

    @pytest.mark.skipif(not HOMEROOM_PNG.exists(), reason="Test PNG not available")
    def test_export_png_with_avatar(self):
        """Export with real avatar image preserves both image and card data."""
        original_card = parse_card_png(HOMEROOM_PNG.read_bytes())

        exported_png = export_card_png(original_card, HOMEROOM_PNG.read_bytes())

        reimported = parse_card_png(exported_png)
        assert reimported.name == original_card.name
        assert reimported.description == original_card.description

    def test_card_to_v2_dict_structure(self):
        card = ParsedCard(name="Struct", tags=["a", "b"])
        d = card_to_v2_dict(card)

        assert d["spec"] == "chara_card_v2"
        assert d["spec_version"] == "2.0"
        assert d["data"]["name"] == "Struct"
        assert d["data"]["tags"] == ["a", "b"]
        assert "first_mes" in d["data"]
