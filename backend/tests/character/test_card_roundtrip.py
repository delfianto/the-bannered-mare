"""Integration tests against every real character card checked into ``characters/``.

Unlike the hand-crafted fixtures in test_card_parser.py / test_service.py, these
exercise the full import -> export -> re-import pipeline against the actual (messy,
creator-authored) cards this project ships as samples -- the same cards that exposed
the export <START>-loss bug and the smart-quote inconsistency.
"""

from pathlib import Path

import pytest
from sqlalchemy.orm import Session
from src.character.card_parser import parse_card_json, split_example_dialogues
from src.character.repository import CharacterRepository
from src.character.service import CharacterService, _title_case_tag
from src.core.persistence.enums import Gender
from src.core.utils.upload import UploadedFile
from src.lore.repository import LoreEntryRepository, LoreRepository
from src.lore.service import LoreService

CARDS_DIR = Path(__file__).parents[3] / "characters"
CARD_FILES = sorted(CARDS_DIR.glob("*.png")) if CARDS_DIR.exists() else []

_SMART_QUOTES = set("‘’“”")


def _service(db: Session) -> CharacterService:
    repo = CharacterRepository(db)
    return CharacterService(repo, LoreService(LoreRepository(db), LoreEntryRepository(db)))


@pytest.mark.skipif(not CARD_FILES, reason="characters/ sample cards not available")
@pytest.mark.parametrize("card_path", CARD_FILES, ids=lambda p: p.stem)
class TestRealCardImportExportRoundtrip:
    @pytest.mark.asyncio
    async def test_import_succeeds_with_a_name(self, db: Session, card_path: Path) -> None:
        service = _service(db)
        upload = UploadedFile(card_path.read_bytes(), card_path.name)

        character = await service.import_card(upload)

        assert character.id
        assert character.name.strip()
        assert character.version == 2

    @pytest.mark.asyncio
    async def test_imported_text_has_no_smart_quotes(self, db: Session, card_path: Path) -> None:
        """Every free-text field normalizes smart quotes -- regression guard for
        the mixed straight/curly quote data found across these cards."""
        service = _service(db)
        upload = UploadedFile(card_path.read_bytes(), card_path.name)
        character = await service.import_card(upload)

        text_fields = [
            character.name,
            character.description,
            character.personality,
            character.first_message,
            character.scenario,
            character.post_history_instructions,
            character.system_prompt,
            character.creator_notes,
            character.creator,
            character.character_version,
        ]
        list_fields = [
            character.example_dialogues or [],
            character.alternate_greetings or [],
            character.tags or [],
        ]

        offenders = [f for f in text_fields if f and (set(f) & _SMART_QUOTES)] + [
            f for values in list_fields for f in values if set(f) & _SMART_QUOTES
        ]
        assert offenders == []

    @pytest.mark.asyncio
    async def test_tags_are_title_cased(self, db: Session, card_path: Path) -> None:
        """Every stored tag must already equal its own title-cased form -- a
        property check rather than hardcoded expected lists, since each card's
        tags differ. Also guards idempotency: re-running the normalizer on
        already-imported data must be a no-op."""
        service = _service(db)
        upload = UploadedFile(card_path.read_bytes(), card_path.name)
        character = await service.import_card(upload)

        for tag in character.tags or []:
            assert tag == _title_case_tag(tag), f"tag not normalized: {tag!r}"

    @pytest.mark.asyncio
    async def test_example_dialogues_survive_export_reimport(
        self, db: Session, card_path: Path
    ) -> None:
        """The exact bug this suite exists to pin down: exporting a character with
        multiple example-dialogue blocks and re-parsing that export must yield the
        same blocks back -- not one block merged from several."""
        service = _service(db)
        upload = UploadedFile(card_path.read_bytes(), card_path.name)
        character = await service.import_card(upload)

        original = character.example_dialogues or []

        exported = service.export_as_json(character.id)
        reparsed = parse_card_json(exported)
        resplit = split_example_dialogues(reparsed.example_dialogues)

        assert resplit == original

    @pytest.mark.asyncio
    async def test_png_export_reimport_preserves_name_and_dialogues(
        self, db: Session, card_path: Path
    ) -> None:
        """Same round-trip guarantee via the PNG path (embedded tEXt chunk)."""
        service = _service(db)
        upload = UploadedFile(card_path.read_bytes(), card_path.name)
        character = await service.import_card(upload)

        png_bytes = service.export_as_png(character.id)
        from src.character.card_parser import parse_card_png

        reimported = parse_card_png(png_bytes)

        assert reimported.name == character.name
        assert split_example_dialogues(reimported.example_dialogues) == (
            character.example_dialogues or []
        )


# Expected (age, gender enum, species) once card_parser's text-extracted strings
# have gone through _build_character_from_card -> _map_card_gender. None means
# "unset" -- three cards have no explicit label anywhere in their text.
_EXPECTED_ATTRIBUTES = {
    "bestfriend_roommate": ("19", Gender.FEMALE, "American"),
    "daro_soraya": (None, None, None),
    "emily": ("20", Gender.FEMALE, None),
    "homeroom_teacher": (None, None, None),
    "kalina": ("19", Gender.FEMALE, None),
    "mina": ("25", Gender.FEMALE, "Human"),
    "mina_stepsister": (None, None, None),
    "shy_cousin": ("19", Gender.FEMALE, None),
}


@pytest.mark.skipif(not CARD_FILES, reason="characters/ sample cards not available")
@pytest.mark.parametrize("card_path", CARD_FILES, ids=lambda p: p.stem)
@pytest.mark.asyncio
async def test_baked_in_attributes_land_on_the_character_row(db: Session, card_path: Path) -> None:
    """DB-level counterpart of test_card_parser's parser-only check: confirms
    the extracted strings survive _build_character_from_card's Gender-enum
    mapping, not just card_parser's own ParsedCard fields."""
    service = _service(db)
    upload = UploadedFile(card_path.read_bytes(), card_path.name)
    character = await service.import_card(upload)

    expected_age, expected_gender, expected_species = _EXPECTED_ATTRIBUTES[card_path.stem]
    assert character.age == expected_age
    assert character.gender == expected_gender
    assert character.species == expected_species


@pytest.mark.skipif(not CARD_FILES, reason="characters/ sample cards not available")
class TestRealCardEmbeddedLorebook:
    @pytest.mark.asyncio
    async def test_daro_soraya_lorebook_imports_all_entries(self, db: Session) -> None:
        """daro_soraya.png embeds a 4-entry character_book -- confirms the lore
        import path (separate from the character-fields path under test above)
        also survives real-card data end to end."""
        card_path = CARDS_DIR / "daro_soraya.png"
        if not card_path.exists():
            pytest.skip("daro_soraya.png not available")

        service = _service(db)
        upload = UploadedFile(card_path.read_bytes(), card_path.name)
        character = await service.import_card(upload)

        lorebooks = service.lore_service.list_for_character_with_entries(character.id)
        assert len(lorebooks) == 1
        assert len(lorebooks[0].entries) == 4
