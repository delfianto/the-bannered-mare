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
    fill_canonical_name,
    fill_prose_inferred_attributes,
    normalize_bullet_list,
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
        # The labeled pass reads ONLY explicit `label:` fields -- daro_soraya's
        # "Khajiit dancer" is prose, so fill_baked_in_attributes leaves it blank.
        # (The separate prose pass DOES recover it -- see TestProseInferredAttributes.)
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


class TestProseInferredAttributes:
    """The lower-confidence second pass: infer species/age/gender from unlabeled
    prose, filling only fields the labeled pass left blank."""

    def test_species_from_prose_vocabulary(self):
        # daro_soraya.png: "Khajiit" is stated in prose, never as a label.
        card = ParsedCard(name="Daro-Soraya", description="A mesmerizing Khajiit dancer.")
        assert fill_prose_inferred_attributes(card).species == "Khajiit"

    @pytest.mark.parametrize(
        ("prose", "expected"),
        [
            ("She is a graceful elven ranger.", "Elf"),
            ("A hulking orc warrior blocks the road.", "Orc"),
            ("He was turned into a vampire centuries ago.", "Vampire"),
            ("A curious android with synthetic skin.", "Android"),
            ("Just a normal human woman.", "Human"),
        ],
    )
    def test_species_vocabulary_variants_normalize_to_canonical(self, prose: str, expected: str):
        assert (
            fill_prose_inferred_attributes(ParsedCard(name="X", description=prose)).species
            == expected
        )

    def test_species_earliest_match_wins(self):
        card = ParsedCard(name="X", description="A human raised among elves in the forest.")
        assert fill_prose_inferred_attributes(card).species == "Human"

    @pytest.mark.parametrize(
        "metaphor",
        [
            "She's an absolute angel.",
            "A total sex demon in bed.",
            "She is a goddess.",
            "A monster of a man.",
        ],
    )
    def test_metaphor_words_are_not_treated_as_species(self, metaphor: str):
        """angel/demon/goddess/monster are figurative here -- excluded from the vocab."""
        assert (
            fill_prose_inferred_attributes(ParsedCard(name="X", description=metaphor)).species == ""
        )

    def test_species_substring_false_positives_are_guarded(self):
        # "self"/"force" contain "elf"/"orc"; word boundaries must prevent a match.
        card = ParsedCard(name="X", description="She forced herself to enforce the law.")
        assert fill_prose_inferred_attributes(card).species == ""

    @pytest.mark.parametrize(
        ("prose", "expected"),
        [
            ("She is a 24 year old woman.", "24"),  # homeroom_teacher.png
            ("A 30-year-old teacher.", "30"),
            ("He's 19yo and reckless.", "19"),
            ("A traveler, aged 42, arrives.", "42"),
        ],
    )
    def test_age_from_prose(self, prose: str, expected: str):
        assert (
            fill_prose_inferred_attributes(ParsedCard(name="X", description=prose)).age == expected
        )

    def test_age_prose_requires_the_old_suffix(self):
        # A bare number is not an age -- "5 years" of experience is not age 5.
        card = ParsedCard(name="X", description="She has 5 years of experience and 3 cats.")
        assert fill_prose_inferred_attributes(card).age == ""

    def test_gender_from_female_pronouns(self):
        card = ParsedCard(name="X", description="She smiled. Her eyes gleamed as she turned.")
        assert fill_prose_inferred_attributes(card).gender == "Female"

    def test_gender_from_male_pronouns(self):
        card = ParsedCard(name="X", description="He nodded. His jaw tightened as he spoke.")
        assert fill_prose_inferred_attributes(card).gender == "Male"

    def test_gender_female_char_survives_male_user_pronouns(self):
        """mina_stepsister.png: a female char whose {{user}} is male. Her she/her
        must still dominate the {{user}}'s scattered he/him."""
        prose = (
            "She mocks him constantly, rolling her eyes at him. "
            "She bites his shoulder, digs her nails into his back, but she loves it. "
            "Her whole vibe says she runs the show."
        )
        assert (
            fill_prose_inferred_attributes(ParsedCard(name="X", description=prose)).gender
            == "Female"
        )

    def test_gender_ambiguous_stays_blank(self):
        # No clear majority -> no call.
        card = ParsedCard(name="X", description="He and she walked. His and her coats matched.")
        assert fill_prose_inferred_attributes(card).gender == ""

    def test_gender_too_little_signal_stays_blank(self):
        card = ParsedCard(name="X", description="A quiet figure by the window.")
        assert fill_prose_inferred_attributes(card).gender == ""

    def test_prose_never_overrides_a_labeled_value(self):
        # Card labels sex Female but prose is full of male pronouns (a male {{user}}).
        card = ParsedCard(
            name="X",
            description="Sex: Female. He grabbed him and told him his fate.",
            gender="Female",  # already set by the labeled pass
            age="25",
            species="Human",
        )
        filled = fill_prose_inferred_attributes(card)
        assert (filled.gender, filled.age, filled.species) == ("Female", "25", "Human")

    def test_custom_gender_blocks_prose_inference(self):
        card = ParsedCard(name="X", description="She is here.", custom_gender="Femboy")
        assert fill_prose_inferred_attributes(card).gender == ""


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


class TestNormalizeBulletList:
    """Bullet-listed character-sheet fields -> blank-line-separated paragraphs."""

    def test_flattened_spaces_become_blank_line_paragraphs(self):
        # The shy_cousin failure mode: newlines collapsed into runs of spaces.
        raw = "- One trait here.       - Two trait here.       - Three trait here.  "
        assert normalize_bullet_list(raw) == (
            "One trait here.\n\nTwo trait here.\n\nThree trait here."
        )

    def test_markdown_newline_bullets_are_reflowed(self):
        assert normalize_bullet_list("- Alpha.\n- Beta.\n- Gamma.") == "Alpha.\n\nBeta.\n\nGamma."

    def test_indented_and_star_markers_are_handled(self):
        assert normalize_bullet_list("* A\n  * B\n  * C") == "A\n\nB\n\nC"

    def test_plain_prose_is_untouched(self):
        prose = "She is shy and quiet. She paused - then left the room."
        assert normalize_bullet_list(prose) == prose

    def test_emphasis_opener_is_not_a_bullet(self):
        # A narrative "*action*" opener must not be mistaken for a "*" bullet: the
        # marker only counts when whitespace follows it.
        text = "*She looks up nervously* and says hi."
        assert normalize_bullet_list(text) == text

    def test_single_bullet_just_loses_its_marker(self):
        assert normalize_bullet_list("- Just one trait.") == "Just one trait."

    def test_empty_string_is_returned_as_is(self):
        assert normalize_bullet_list("") == ""

    def test_applied_to_personality_and_description_on_import(self):
        v2 = {
            "data": {
                "name": "Bulleted",
                "personality": "- Kind.       - Brave.",
                "description": "- Tall.       - Freckled.",
                "scenario": "- left alone on purpose -",
            },
        }
        card = parse_card_json(v2)
        assert card.personality == "Kind.\n\nBrave."
        assert card.description == "Tall.\n\nFreckled."
        # Only the character-sheet fields are normalized; scenario is left as-is.
        assert card.scenario == "- left alone on purpose -"


class TestFillCanonicalName:
    """Recover the character's real name from a role/title `name` field. `name` doubles
    as the {{char}} token and the storefront listing, so it's often SEO junk or a bare
    role while the real name hides in the prose."""

    def test_clean_name_is_left_untouched(self):
        # An unrelated name mentioned in the prose must NOT flip a good name.
        for good in ("Emily", "Kalina", "Daro-Soraya", "Mina"):
            card = ParsedCard(name=good, description="Name: Somebody Else")
            assert fill_canonical_name(card).name == good

    def test_clean_name_upgraded_to_its_fuller_labeled_form(self):
        # The PList/W++ "name(...)" form, spelling a first name out longer.
        card = ParsedCard(name="Mina", description="[{{char}} name(Mina Eun-Hee); age(23)]")
        assert fill_canonical_name(card).name == "Mina Eun-Hee"

    def test_title_is_stripped_off_the_name(self):
        card = ParsedCard(name="Mina — Your Mean and Bratty Stepsister Catches you Sleeping")
        assert fill_canonical_name(card).name == "Mina"

    def test_name_recovered_from_label_in_description(self):
        card = ParsedCard(name="Shy Cousin", description="✨ Character Name: Elara Voss\nAge: 19")
        assert fill_canonical_name(card).name == "Elara Voss"

    def test_label_beats_a_role_leading_segment(self):
        # "Bestfriend / roommate" splits to a role, so the labeled name must win.
        card = ParsedCard(name="Bestfriend / roommate", description="**Name:** Hazel Smith")
        assert fill_canonical_name(card).name == "Hazel Smith"

    def test_anonymous_role_with_no_recoverable_name_is_kept(self):
        card = ParsedCard(
            name="Your Young Homeroom Teacher", description="A teacher. No name given."
        )
        assert fill_canonical_name(card).name == "Your Young Homeroom Teacher"

    def test_label_never_matches_nickname_or_username(self):
        card = ParsedCard(name="Shy Cousin", description="Nickname: Bug\nUsername: cuzz")
        assert fill_canonical_name(card).name == "Shy Cousin"

    def test_full_pipeline_applies_name_recovery(self):
        v2 = {"data": {"name": "Mina — Your Bratty Stepsister", "description": "hi"}}
        assert parse_card_json(v2).name == "Mina"

    # --- "get the fullest name" regressions: each of these returned the WRONG value
    # before _labeled_name_candidates replaced the first-match-only lookup. ---

    def test_picks_fullest_when_a_partial_label_appears_first(self):
        card = ParsedCard(name="Shy Cousin", description="Name: Elara\nName: Elara Voss")
        assert fill_canonical_name(card).name == "Elara Voss"

    def test_combines_split_first_and_last_labels(self):
        card = ParsedCard(name="Shy Cousin", description="First Name: Elara\nLast Name: Voss")
        assert fill_canonical_name(card).name == "Elara Voss"

    def test_user_scoped_label_is_not_stolen_for_the_character(self):
        # "Your name: Jason" is {{user}}, not the character -- must be skipped.
        card = ParsedCard(name="Shy Cousin", description="Your name: Jason\nHer name: Elara Voss")
        assert fill_canonical_name(card).name == "Elara Voss"

    def test_handle_only_labels_recover_nothing(self):
        card = ParsedCard(name="Shy Cousin", description="Username: cuzz99\nNickname: Ellie")
        assert fill_canonical_name(card).name == "Shy Cousin"

    @pytest.mark.parametrize(
        "value",
        ["Elara the Shy Cousin", "Elara, the shy cousin", "Elara — Shy Cousin", "Elara aka Ellie"],
    )
    def test_salvages_leading_name_from_a_trailing_clause(self, value: str):
        card = ParsedCard(name="Shy Cousin", description=f"Name: {value}")
        assert fill_canonical_name(card).name == "Elara"

    def test_salvage_does_not_fire_when_the_name_is_last(self):
        # "Big Sister Yuki" has no connector/separator, so salvaging a leading "Big"
        # would be wrong -- leave the original name instead.
        card = ParsedCard(name="Shy Cousin", description="Name: Big Sister Yuki")
        assert fill_canonical_name(card).name == "Shy Cousin"


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


# Expected (age, gender, species) after the FULL parse (labeled + prose fallback),
# keyed by filename stem. Prose inference now recovers what these creators wrote in
# sentences instead of fields: daro_soraya's "Khajiit" + she/her, homeroom's "24
# year old woman", the stepsister's she/her. Cards that state neither a label nor
# prose for a field stay correctly blank (daro/stepsister have no age at all).
_EXPECTED_CARD_ATTRIBUTES = {
    "bestfriend_roommate": ("19", "Female", ""),  # "Ethnicity: American" is not a species
    "daro_soraya": ("", "Female", "Khajiit"),  # both inferred from prose
    "emily": ("20", "Female", ""),
    "homeroom_teacher": ("24", "Female", ""),  # "a 24 year old woman" (prose)
    "kalina": ("19", "Female", ""),
    "mina": ("25", "Female", "Human"),
    "mina_stepsister": ("", "Female", ""),  # she/her despite a male {{user}}
    "shy_cousin": ("19", "Female", ""),
}


@pytest.mark.skipif(not CARD_FILES, reason="characters/ sample cards not available")
@pytest.mark.parametrize("card_path", CARD_FILES, ids=lambda p: p.stem)
def test_card_attributes_extracted_from_real_cards(card_path: Path):
    card = parse_card_png(card_path.read_bytes())
    assert (card.age, card.gender, card.species) == _EXPECTED_CARD_ATTRIBUTES[card_path.stem]


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
