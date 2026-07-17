"""Tests for CharacterService"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.orm import Session
from src.character import Character, CharacterRepository, CharacterService
from src.character.card_parser import parse_card_json, split_example_dialogues
from src.character.schemas import CharacterFormBase
from src.character.service import _map_card_gender, _normalize_tags, _title_case_tag
from src.core.exceptions import BanneredMareException
from src.core.persistence.enums import Gender
from src.core.utils.upload import UploadedFile
from src.lore.repository import LoreEntryRepository, LoreRepository
from src.lore.service import LoreService


class TestCharacterService:
    """Test suite for CharacterService"""

    def test_list_all(self, db: Session) -> None:
        """Test listing all characters"""
        # Create test characters
        char1 = Character(name="Alice", description="Test character 1")
        char2 = Character(name="Bob", description="Test character 2")
        db.add_all([char1, char2])
        db.commit()

        # Test
        repo = CharacterRepository(db)
        service = CharacterService(
            repo, LoreService(LoreRepository(repo.db), LoreEntryRepository(repo.db))
        )
        characters = service.list_all()

        assert len(characters) == 2
        assert any(c.name == "Alice" for c in characters)
        assert any(c.name == "Bob" for c in characters)

    def test_get_by_id_success(self, db: Session) -> None:
        """Test getting a character by ID successfully"""
        char = Character(name="Alice", description="Test character")
        db.add(char)
        db.commit()
        db.refresh(char)

        repo = CharacterRepository(db)
        service = CharacterService(
            repo, LoreService(LoreRepository(repo.db), LoreEntryRepository(repo.db))
        )
        result = service.get_by_id(char.id)

        assert result.id == char.id
        assert result.name == "Alice"
        assert result.description == "Test character"

    def test_get_by_id_not_found(self, db: Session) -> None:
        """Test getting a character that doesn't exist raises 404"""
        repo = CharacterRepository(db)
        service = CharacterService(
            repo, LoreService(LoreRepository(repo.db), LoreEntryRepository(repo.db))
        )

        with pytest.raises(BanneredMareException) as exc_info:
            _ = service.get_by_id("nonexistent-id")

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_create_character_basic(self, db: Session) -> None:
        """Test creating a character with basic fields"""
        repo = CharacterRepository(db)
        service = CharacterService(
            repo, LoreService(LoreRepository(repo.db), LoreEntryRepository(repo.db))
        )

        character = await service.create(
            CharacterFormBase(
                name="Alice",
                description="A friendly AI",
                personality="Helpful and kind",
                first_message="Hello! How can I help you?",
            )
        )

        assert character.name == "Alice"
        assert character.description == "A friendly AI"
        assert character.personality == "Helpful and kind"
        assert character.first_message == "Hello! How can I help you?"
        assert character.id is not None

    @pytest.mark.asyncio
    async def test_create_character_with_json_fields(self, db: Session) -> None:
        """Test creating a character with JSON fields"""
        repo = CharacterRepository(db)
        service = CharacterService(
            repo, LoreService(LoreRepository(repo.db), LoreEntryRepository(repo.db))
        )

        dialogues = json.dumps(["<START>\nUser: Hi\nAssistant: Hello!"])
        greetings = json.dumps(["Hi there!", "Greetings!"])

        character = await service.create(
            CharacterFormBase(
                name="Alice",
                example_dialogues=dialogues,
                alternate_greetings=greetings,
            )
        )

        assert character.example_dialogues == ["<START>\nUser: Hi\nAssistant: Hello!"]
        assert character.alternate_greetings == ["Hi there!", "Greetings!"]

    @pytest.mark.asyncio
    async def test_create_character_invalid_json(self, db: Session) -> None:
        """Test creating a character with invalid JSON raises error"""
        repo = CharacterRepository(db)
        service = CharacterService(
            repo, LoreService(LoreRepository(repo.db), LoreEntryRepository(repo.db))
        )

        with pytest.raises(BanneredMareException) as exc_info:
            _ = await service.create(
                CharacterFormBase(name="Alice", example_dialogues="invalid json {")
            )

        assert exc_info.value.status_code == 422
        assert "Invalid JSON" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_create_character_with_avatar(self, db: Session) -> None:
        """Test creating a character with avatar upload"""
        repo = CharacterRepository(db)
        service = CharacterService(
            repo, LoreService(LoreRepository(repo.db), LoreEntryRepository(repo.db))
        )

        mock_file = UploadedFile(b"fake png avatar bytes", "avatar.png")

        with patch(
            "src.character.service.save_character_avatar",
            new_callable=AsyncMock,
            return_value=(
                "avatars/char_123/avatar.png",
                "avatars/char_123/avatar_large.jpg",
                "avatars/char_123/avatar_thumbnail.jpg",
            ),
        ):
            character = await service.create(
                CharacterFormBase(name="Alice"),
                avatar=mock_file,
            )

            assert character.avatar == "avatars/char_123/avatar.png"
            assert character.avatar_large == "avatars/char_123/avatar_large.jpg"
            assert character.avatar_thumbnail == "avatars/char_123/avatar_thumbnail.jpg"

    @pytest.mark.asyncio
    async def test_update_character_basic_fields(self, db: Session) -> None:
        """Test updating character basic fields"""
        char = Character(name="Alice", description="Old description")
        db.add(char)
        db.commit()
        db.refresh(char)

        repo = CharacterRepository(db)
        service = CharacterService(
            repo, LoreService(LoreRepository(repo.db), LoreEntryRepository(repo.db))
        )
        updated = await service.update(
            char.id,
            CharacterFormBase(name="Alice Updated", description="New description"),
        )

        assert updated.name == "Alice Updated"
        assert updated.description == "New description"

    @pytest.mark.asyncio
    async def test_update_character_partial(self, db: Session) -> None:
        """Test updating only some fields"""
        char = Character(
            name="Alice",
            description="Description",
            personality="Friendly",
        )
        db.add(char)
        db.commit()
        db.refresh(char)

        repo = CharacterRepository(db)
        service = CharacterService(
            repo, LoreService(LoreRepository(repo.db), LoreEntryRepository(repo.db))
        )
        updated = await service.update(
            char.id, CharacterFormBase(description="Updated description")
        )

        assert updated.name == "Alice"  # Unchanged
        assert updated.description == "Updated description"  # Changed
        assert updated.personality == "Friendly"  # Unchanged

    @pytest.mark.asyncio
    async def test_update_character_json_fields(self, db: Session) -> None:
        """Test updating JSON fields"""
        char = Character(name="Alice")
        db.add(char)
        db.commit()
        db.refresh(char)

        repo = CharacterRepository(db)
        service = CharacterService(
            repo, LoreService(LoreRepository(repo.db), LoreEntryRepository(repo.db))
        )
        greetings = json.dumps(["Hello!", "Hi!"])
        updated = await service.update(char.id, CharacterFormBase(alternate_greetings=greetings))

        assert updated.alternate_greetings == ["Hello!", "Hi!"]

    @pytest.mark.asyncio
    async def test_update_character_not_found(self, db: Session) -> None:
        """Test updating non-existent character raises 404"""
        repo = CharacterRepository(db)
        service = CharacterService(
            repo, LoreService(LoreRepository(repo.db), LoreEntryRepository(repo.db))
        )

        with pytest.raises(BanneredMareException) as exc_info:
            _ = await service.update("nonexistent-id", CharacterFormBase(name="New Name"))

        assert exc_info.value.status_code == 404

    def test_delete_character_success(self, db: Session) -> None:
        """Test deleting a character successfully"""
        char = Character(name="Alice")
        db.add(char)
        db.commit()
        db.refresh(char)
        char_id = char.id

        repo = CharacterRepository(db)
        service = CharacterService(
            repo, LoreService(LoreRepository(repo.db), LoreEntryRepository(repo.db))
        )

        with patch("src.character.service.delete_character_files"):
            service.delete(char_id)

        # Verify character is deleted
        deleted = db.query(Character).filter(Character.id == char_id).first()
        assert deleted is None

    def test_delete_character_not_found(self, db: Session) -> None:
        """Test deleting non-existent character raises 404"""
        repo = CharacterRepository(db)
        service = CharacterService(
            repo, LoreService(LoreRepository(repo.db), LoreEntryRepository(repo.db))
        )

        with pytest.raises(BanneredMareException) as exc_info:
            service.delete("nonexistent-id")

        assert exc_info.value.status_code == 404

    def test_parse_json_field_valid(self, db: Session) -> None:
        """Test JSON field parsing with valid JSON"""
        repo = CharacterRepository(db)
        service = CharacterService(
            repo, LoreService(LoreRepository(repo.db), LoreEntryRepository(repo.db))
        )
        result = service._parse_json_field('{"key": "value"}', "test_field")  # pyright: ignore[reportPrivateUsage]
        assert result == {"key": "value"}

    def test_parse_json_field_none(self, db: Session) -> None:
        """Test JSON field parsing with None returns None"""
        repo = CharacterRepository(db)
        service = CharacterService(
            repo, LoreService(LoreRepository(repo.db), LoreEntryRepository(repo.db))
        )
        result = service._parse_json_field(None, "test_field")  # pyright: ignore[reportPrivateUsage]
        assert result is None

    def test_parse_json_field_invalid(self, db: Session) -> None:
        """Test JSON field parsing with invalid JSON raises error"""
        repo = CharacterRepository(db)
        service = CharacterService(
            repo, LoreService(LoreRepository(repo.db), LoreEntryRepository(repo.db))
        )

        with pytest.raises(BanneredMareException) as exc_info:
            _ = service._parse_json_field("invalid json", "test_field")  # pyright: ignore[reportPrivateUsage]

        assert exc_info.value.status_code == 422
        assert "test_field" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_import_card_json(self, db: Session) -> None:
        """Test importing a V2 JSON character card"""
        repo = CharacterRepository(db)
        service = CharacterService(
            repo, LoreService(LoreRepository(repo.db), LoreEntryRepository(repo.db))
        )

        v2_card = json.dumps(
            {
                "spec": "chara_card_v2",
                "spec_version": "2.0",
                "data": {
                    "name": "Imported Hero",
                    "description": "A brave adventurer",
                    "personality": "Bold and courageous",
                    "first_mes": "Greetings, traveler!",
                    "mes_example": "<START>\nUser: Hello\nHero: Well met!",
                    "scenario": "A fantasy world",
                    "system_prompt": "You are a brave hero.",
                    "post_history_instructions": "",
                    "creator_notes": "Test card",
                    "creator": "Tester",
                    "character_version": "1.0",
                    "alternate_greetings": ["Hail!", "Welcome!"],
                    "tags": ["fantasy", "hero"],
                    "extensions": {},
                },
            }
        )

        mock_file = UploadedFile(v2_card.encode("utf-8"), "hero.json")

        character = await service.import_card(mock_file)

        assert character.name == "Imported Hero"
        assert character.description == "A brave adventurer"
        assert character.personality == "Bold and courageous"
        assert character.first_message == "Greetings, traveler!"
        assert character.scenario == "A fantasy world"
        assert character.system_prompt == "You are a brave hero."
        assert character.creator == "Tester"
        assert character.alternate_greetings == ["Hail!", "Welcome!"]
        # Tags are title-cased on import so casing stays consistent across cards.
        assert character.tags == ["Fantasy", "Hero"]
        assert character.version == 2
        # Import splits mes_example on <START> and strips the marker per block.
        assert character.example_dialogues == ["User: Hello\nHero: Well met!"]

    @pytest.mark.asyncio
    async def test_import_export_reimport_preserves_example_dialogue_count(
        self, db: Session
    ) -> None:
        """A card with multiple <START> blocks must survive import -> export ->
        re-import with the same block count -- the export path used to join blocks
        with a bare "\\n" and drop the <START> markers, silently merging every
        example back into one on re-import."""
        repo = CharacterRepository(db)
        service = CharacterService(
            repo, LoreService(LoreRepository(repo.db), LoreEntryRepository(repo.db))
        )

        v2_card = json.dumps(
            {
                "data": {
                    "name": "Roundtrip Hero",
                    "mes_example": (
                        "<START>\nUser: Hi\nHero: Hello!"
                        "<START>\nUser: Bye\nHero: Farewell!"
                        "<START>\nUser: Help!\nHero: On my way!"
                    ),
                }
            }
        )
        character = await service.import_card(UploadedFile(v2_card.encode("utf-8"), "hero.json"))
        assert character.example_dialogues is not None
        assert len(character.example_dialogues) == 3

        exported = json.loads(service.export_as_json(character.id))
        reparsed = parse_card_json(exported)
        resplit = split_example_dialogues(reparsed.example_dialogues)

        assert resplit == character.example_dialogues

    def test_export_as_json(self, db: Session) -> None:
        """Test exporting a character as TavernCard V2 JSON"""
        # example_dialogues holds post-import blocks (marker already stripped, per
        # split_example_dialogues) — mirrors what import_card actually stores, not
        # a hand-crafted string with <START> baked in.
        char = Character(
            name="Export Test",
            description="A test character for export",
            personality="Friendly",
            first_message="Hello there!",
            scenario="Modern day",
            creator="Tester",
            alternate_greetings=["Hey!", "Hi!"],
            tags=["test"],
            example_dialogues=["User: Hi\nChar: Hello!", "User: Bye\nChar: Cya!"],
        )
        db.add(char)
        db.commit()
        db.refresh(char)

        repo = CharacterRepository(db)
        service = CharacterService(
            repo, LoreService(LoreRepository(repo.db), LoreEntryRepository(repo.db))
        )
        json_str = service.export_as_json(char.id)

        exported = json.loads(json_str)
        assert exported["spec"] == "chara_card_v2"
        assert exported["spec_version"] == "2.0"
        data = exported["data"]
        assert data["name"] == "Export Test"
        assert data["description"] == "A test character for export"
        assert data["personality"] == "Friendly"
        assert data["first_mes"] == "Hello there!"
        assert data["scenario"] == "Modern day"
        assert data["creator"] == "Tester"
        assert data["alternate_greetings"] == ["Hey!", "Hi!"]
        assert data["tags"] == ["test"]
        # Each stored block gets its own <START> back, so re-splitting the exported
        # mes_example reconstructs the exact same two blocks (the round-trip bug:
        # a bare "\n".join would merge them into one on re-import).
        assert (
            data["mes_example"] == "<START>\nUser: Hi\nChar: Hello!\n<START>\nUser: Bye\nChar: Cya!"
        )

    @pytest.mark.asyncio
    async def test_import_and_export_character_book(self, db: Session) -> None:
        """Test importing and exporting a V2 JSON card with a character_book"""
        repo = CharacterRepository(db)
        service = CharacterService(
            repo, LoreService(LoreRepository(repo.db), LoreEntryRepository(repo.db))
        )

        v2_card = json.dumps(
            {
                "spec": "chara_card_v2",
                "spec_version": "2.0",
                "data": {
                    "name": "Lore Keeper",
                    "description": "Guardian of the library",
                    "personality": "Wise",
                    "character_book": {
                        "name": "Keeper's Lore",
                        "description": "Library details",
                        "entries": [
                            {
                                "keys": ["library", "books"],
                                "content": "The library houses ancient spells.",
                                "constant": False,
                                "enabled": True,
                                "name": "Ancient Spells",
                                "priority": 150,
                            }
                        ],
                    },
                },
            }
        )

        mock_file = UploadedFile(v2_card.encode("utf-8"), "keeper.json")

        character = await service.import_card(mock_file)
        assert character.name == "Lore Keeper"

        # Verify lorebook was created in the database
        from sqlalchemy import select
        from src.lore.models import Lorebook

        lorebook = (
            db.execute(select(Lorebook).where(Lorebook.character_id == character.id))
            .scalars()
            .first()
        )

        assert lorebook is not None
        assert lorebook.name == "Keeper's Lore"
        assert lorebook.description == "Library details"
        assert len(lorebook.entries) == 1
        assert lorebook.entries[0].keys == ["library", "books"]
        assert lorebook.entries[0].content == "The library houses ancient spells."

        # Now test exporting the same character back to json and verify character_book exists
        db.refresh(character)
        json_str = service.export_as_json(character.id)
        exported = json.loads(json_str)

        assert exported["data"]["character_book"]["name"] == "Keeper's Lore"
        assert exported["data"]["character_book"]["entries"][0]["name"] == "Ancient Spells"
        assert exported["data"]["character_book"]["entries"][0]["keys"] == ["library", "books"]

    @pytest.mark.asyncio
    async def test_import_and_export_custom_fields(self, db):
        from src.core.persistence.enums import Gender

        repo = CharacterRepository(db)
        service = CharacterService(
            repo, LoreService(LoreRepository(repo.db), LoreEntryRepository(repo.db))
        )

        # 1. Test importing a card with species, age, gender in extensions
        v2_card = json.dumps(
            {
                "spec": "chara_card_v2",
                "spec_version": "2.0",
                "data": {
                    "name": "Custom Elf",
                    "extensions": {
                        "bannered_mare": {
                            "species": "Altmer",
                            "gender": "female",
                            "age": "130",
                        }
                    },
                },
            }
        )

        mock_file = UploadedFile(v2_card.encode("utf-8"), "elf.json")

        character = await service.import_card(mock_file)
        assert character.name == "Custom Elf"
        assert character.species == "Altmer"
        assert character.gender == Gender.FEMALE
        assert character.age == "130"

        # 2. Test exporting a character with custom fields
        db.refresh(character)
        json_str = service.export_as_json(character.id)
        exported = json.loads(json_str)

        assert exported["data"]["extensions"]["bannered_mare"]["species"] == "Altmer"
        assert exported["data"]["extensions"]["bannered_mare"]["gender"] == "female"
        assert exported["data"]["extensions"]["bannered_mare"]["age"] == "130"
        assert exported["data"]["extensions"]["species"] == "Altmer"
        assert exported["data"]["extensions"]["gender"] == "female"
        assert exported["data"]["extensions"]["age"] == "130"


class TestMapCardGender:
    """Unit tests for the consolidated card gender mapper (import path)."""

    @pytest.mark.parametrize(
        ("gender", "custom_gender", "expected"),
        [
            # Recognized values map to their enum member (same lookup as create path).
            ("male", "", (Gender.MALE, None)),
            ("female", "", (Gender.FEMALE, None)),
            ("non-binary", "", (Gender.NON_BINARY, None)),
            ("MALE", "", (Gender.MALE, None)),
            ("  female  ", "", (Gender.FEMALE, None)),
            # Unknown label -> OTHERS, original string kept verbatim as the custom label.
            ("Attack Helicopter", "", (Gender.OTHERS, "Attack Helicopter")),
            # The literal "others" is treated as a custom label, not a recognized gender.
            ("others", "", (Gender.OTHERS, "others")),
            # No card gender: fall back to a free-text custom_gender if present.
            ("", "femboy", (Gender.OTHERS, "femboy")),
            ("", "", (None, None)),
            (None, None, (None, None)),
        ],
    )
    def test_map_card_gender(
        self,
        gender: str | None,
        custom_gender: str | None,
        expected: tuple[Gender | None, str | None],
    ) -> None:
        assert _map_card_gender(gender, custom_gender) == expected

    def test_card_gender_takes_precedence_over_custom(self) -> None:
        """A recognized card gender wins; custom_gender is ignored when gender is set."""
        assert _map_card_gender("male", "ignored") == (Gender.MALE, None)


class TestNormalizeTags:
    """Unit tests for tag Title-Casing (import + create/update paths)."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            # Plain casing variants.
            ("cute", "Cute"),
            ("ENGLISH", "English"),
            ("Already Title Case", "Already Title Case"),
            # Known domain acronyms canonicalize to uppercase regardless of how a
            # given card cased them -- so "OC" (homeroom_teacher.png) and "oc"
            # (emily.png) land as the same tag, not two different strings.
            ("NSFW", "NSFW"),
            ("nsfw", "NSFW"),
            ("OC", "OC"),
            ("oc", "OC"),
            ("Any POV", "Any POV"),
            ("anypov", "Anypov"),  # doesn't merge with "Any POV" -- different word
            ("SFW <-> NSFW", "SFW <-> NSFW"),
            # An all-caps word outside the known set is still preserved if it's
            # acronym-length -- a plausible acronym we just don't have on file.
            ("AU", "AU"),
            # Hyphens split into separately-capitalized words; other punctuation
            # (commas, parens) is left in place, only letter-runs are touched.
            ("elder-scrolls", "Elder-Scrolls"),
            ("can be wholesome, can be sexy", "Can Be Wholesome, Can Be Sexy"),
            # Idempotent on data from the real sample cards (already-correct tags
            # from homeroom_teacher.png / kalina.png / mina_stepsister.png).
            ("Gentle Femdom", "Gentle Femdom"),
            ("Possible Saviorfagging", "Possible Saviorfagging"),
            ("stepcest", "Stepcest"),
        ],
    )
    def test_title_case_tag(self, raw: str, expected: str) -> None:
        assert _title_case_tag(raw) == expected

    def test_normalize_tags_maps_every_tag(self) -> None:
        assert _normalize_tags(["cute", "NSFW", "black hair"]) == ["Cute", "NSFW", "Black Hair"]

    def test_normalize_tags_passes_none_and_empty_through(self) -> None:
        assert _normalize_tags(None) is None
        assert _normalize_tags([]) == []
