"""Tests for character card parser — V1/V2 PNG and JSON import/export."""

import json
from pathlib import Path

import pytest
from src.character.card_parser import (
    ParsedCard,
    card_to_v2_dict,
    export_card_json,
    export_card_png,
    fill_baked_in_attributes,
    parse_card_json,
    parse_card_png,
    split_example_dialogues,
)

HOMEROOM_PNG = Path(__file__).parent.parent / "data" / "homeroom.png"

# The real, creator-authored sample cards checked into ./characters at the repo
# root -- the same ones that surfaced the smart-quote and <START>-loss bugs.
# Exercised here as pure parser input (no DB); test_card_roundtrip.py covers the
# full import/export pipeline against the same files.
CARDS_DIR = Path(__file__).parents[3] / "characters"
CARD_FILES = sorted(CARDS_DIR.glob("*.png")) if CARDS_DIR.exists() else []
_SMART_QUOTES = set("‘’“”")


class TestSplitExampleDialogues:
    def test_empty(self):
        assert split_example_dialogues("") == []
        assert split_example_dialogues("   \n  ") == []

    def test_no_marker_is_single_block(self):
        assert split_example_dialogues("Just one example.") == ["Just one example."]

    def test_splits_on_start_and_drops_empties(self):
        raw = "<START>\nUser: hi\nChar: hello<START>\nUser: bye\nChar: cya<START>\n  "
        assert split_example_dialogues(raw) == [
            "User: hi\nChar: hello",
            "User: bye\nChar: cya",
        ]

    def test_leading_marker_produces_no_empty_first_block(self):
        assert split_example_dialogues("<START>\nfreeform text") == ["freeform text"]


class TestFillBakedInAttributes:
    """Real conventions from the sample cards (bracket-attribute, markdown-bold,
    emoji-label), plus guards against the risk of a wrong extraction writing bad
    data into a filterable field."""

    def test_bracket_attribute_format(self):
        # mina.png
        card = ParsedCard(
            name="Mina",
            description="[{{char}} name(Mina Eun-Hee);\n{{char}} sex(Female);"
            "\n{{char}} race(Human);\n{{char}} age(25);",
        )
        filled = fill_baked_in_attributes(card)
        assert filled.age == "25"
        assert filled.gender == "Female"
        assert filled.species == "Human"

    def test_markdown_bold_format(self):
        # bestfriend_roommate.png -- "Ethnicity: American" is a nationality, not a
        # species, and there is no ethnicity column to hold it, so species stays
        # blank rather than being polluted (see test_ethnicity_label_is_not_species).
        card = ParsedCard(
            name="Hazel",
            description="**Name:** Hazel Smith\n**Age:** 19\n**Sex:** Female"
            "\n**Ethnicity:** American\n**Occupation:** Roommate",
        )
        filled = fill_baked_in_attributes(card)
        assert filled.age == "19"
        assert filled.gender == "Female"
        assert filled.species == ""

    def test_emoji_label_format(self):
        # emily.png / shy_cousin.png
        card = ParsedCard(
            name="Emily",
            description="✨ Character Name: Emily\n🎂 Age: 20\n🚻 Gender: Female\n💼 Occupation: Student",
        )
        filled = fill_baked_in_attributes(card)
        assert filled.age == "20"
        assert filled.gender == "Female"
        assert filled.species == ""  # no race/species label present

    def test_ethnicity_label_is_not_species(self):
        """An "Ethnicity"/"Nationality" label must NOT populate species -- those
        carry real-world nationalities ("American", "Korean") on the human cards
        that dominate the corpus, and there is no ethnicity column to route them
        to. Only "race"/"species" feed the species field."""
        for label in ("Ethnicity", "Nationality"):
            card = ParsedCard(name="X", description=f"**{label}:** American")
            assert fill_baked_in_attributes(card).species == ""

    def test_no_label_stays_blank(self):
        # daro_soraya.png: race is only mentioned in prose ("Khajiit dancer"),
        # never as an explicit label -- must not be guessed at.
        card = ParsedCard(
            name="Daro-Soraya",
            description="A mesmerizing Khajiit dancer from a nomadic caravan.",
        )
        filled = fill_baked_in_attributes(card)
        assert filled.age == ""
        assert filled.gender == ""
        assert filled.species == ""

    @pytest.mark.parametrize(
        "word",
        ["engage", "average", "trace", "embrace", "manage", "stage", "wage"],
    )
    def test_common_words_containing_label_substrings_are_not_matched(self, word: str):
        """ "age"/"race" are substrings of common English words -- the extractor
        must require a word boundary, or e.g. "manage: something" would falsely
        read as an age field."""
        card = ParsedCard(name="X", description=f"They {word}: something happens next.")
        filled = fill_baked_in_attributes(card)
        assert filled.age == ""
        assert filled.species == ""

    def test_extension_values_take_priority_over_text_extraction(self):
        """A card that sets both the explicit extension AND a baked-in text label
        must keep the extension's value -- higher confidence, explicit signal."""
        card = ParsedCard(
            name="X",
            description="**Age:** 19\n**Sex:** Female",
            age="30",
            gender="Non-binary",
        )
        filled = fill_baked_in_attributes(card)
        assert filled.age == "30"
        assert filled.gender == "Non-binary"

    def test_custom_gender_also_blocks_text_extraction(self):
        card = ParsedCard(name="X", description="**Sex:** Female", custom_gender="Femboy")
        filled = fill_baked_in_attributes(card)
        assert filled.gender == ""  # custom_gender already carries the signal

    def test_falls_back_to_personality_when_description_has_no_labels(self):
        card = ParsedCard(name="X", description="Just a story.", personality="**Age:** 42")
        filled = fill_baked_in_attributes(card)
        assert filled.age == "42"


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

    def test_smart_quotes_normalized_to_ascii(self):
        v2 = {
            "data": {
                "name": "Quoted",
                "description": "She said “hello” and it’s ‘fine’.",
                "mes_example": "“Hi”",
                "tags": ["can’t stop", "plain"],
            },
        }
        card = parse_card_json(v2)

        assert card.description == "She said \"hello\" and it's 'fine'."
        assert card.example_dialogues == '"Hi"'
        assert card.tags == ["can't stop", "plain"]


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


@pytest.mark.skipif(not CARD_FILES, reason="characters/ sample cards not available")
@pytest.mark.parametrize("card_path", CARD_FILES, ids=lambda p: p.stem)
class TestAllSampleCards:
    """Parser-only smoke + normalization coverage across every card in characters/."""

    def test_parses_without_error(self, card_path: Path):
        card = parse_card_png(card_path.read_bytes())
        assert card.name.strip()
        assert card.spec == "chara_card_v2"

    def test_no_smart_quotes_survive_parsing(self, card_path: Path):
        card = parse_card_png(card_path.read_bytes())

        text_fields = [
            card.name,
            card.description,
            card.personality,
            card.first_message,
            card.example_dialogues,
            card.scenario,
            card.system_prompt,
            card.post_history_instructions,
            card.creator_notes,
            card.creator,
            card.character_version,
        ]
        list_fields = [card.alternate_greetings, card.tags]

        assert not any(set(f) & _SMART_QUOTES for f in text_fields if f)
        assert not any(set(v) & _SMART_QUOTES for values in list_fields for v in values)

    def test_mes_example_split_round_trips_through_export(self, card_path: Path):
        """card_parser-level guarantee: whatever split_example_dialogues() would
        produce from the parsed mes_example survives export_card_json + re-parse,
        independent of the DB layer's list<->string conversion."""
        card = parse_card_png(card_path.read_bytes())
        original_blocks = split_example_dialogues(card.example_dialogues)

        reparsed = parse_card_json(export_card_json(card))
        assert split_example_dialogues(reparsed.example_dialogues) == original_blocks


# Expected (age, gender, species) after fill_baked_in_attributes, keyed by
# filename stem -- three cards have no explicit label anywhere and must stay
# blank (daro_soraya's "Khajiit" is prose-only, never labeled).
_EXPECTED_BAKED_IN_ATTRIBUTES = {
    "bestfriend_roommate": ("19", "Female", ""),  # "Ethnicity: American" is not a species
    "daro_soraya": ("", "", ""),
    "emily": ("20", "Female", ""),
    "homeroom_teacher": ("", "", ""),
    "kalina": ("19", "Female", ""),
    "mina": ("25", "Female", "Human"),
    "mina_stepsister": ("", "", ""),
    "shy_cousin": ("19", "Female", ""),
}


@pytest.mark.skipif(not CARD_FILES, reason="characters/ sample cards not available")
@pytest.mark.parametrize("card_path", CARD_FILES, ids=lambda p: p.stem)
def test_baked_in_attributes_extracted_from_real_cards(card_path: Path):
    card = parse_card_png(card_path.read_bytes())
    assert (card.age, card.gender, card.species) == _EXPECTED_BAKED_IN_ATTRIBUTES[card_path.stem]


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
