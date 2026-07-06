"""Tests for CharacterService"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.character import Character, CharacterRepository, CharacterService


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
        service = CharacterService(repo)
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
        service = CharacterService(repo)
        result = service.get_by_id(char.id)

        assert result.id == char.id
        assert result.name == "Alice"
        assert result.description == "Test character"

    def test_get_by_id_not_found(self, db: Session) -> None:
        """Test getting a character that doesn't exist raises 404"""
        repo = CharacterRepository(db)
        service = CharacterService(repo)

        with pytest.raises(HTTPException) as exc_info:
            _ = service.get_by_id("nonexistent-id")

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_create_character_basic(self, db: Session) -> None:
        """Test creating a character with basic fields"""
        repo = CharacterRepository(db)
        service = CharacterService(repo)

        character = await service.create(
            name="Alice",
            description="A friendly AI",
            personality="Helpful and kind",
            first_message="Hello! How can I help you?",
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
        service = CharacterService(repo)

        dialogues = json.dumps(["<START>\nUser: Hi\nAssistant: Hello!"])
        greetings = json.dumps(["Hi there!", "Greetings!"])

        character = await service.create(
            name="Alice",
            example_dialogues=dialogues,
            alternate_greetings=greetings,
        )

        assert character.example_dialogues == ["<START>\nUser: Hi\nAssistant: Hello!"]
        assert character.alternate_greetings == ["Hi there!", "Greetings!"]

    @pytest.mark.asyncio
    async def test_create_character_invalid_json(self, db: Session) -> None:
        """Test creating a character with invalid JSON raises error"""
        repo = CharacterRepository(db)
        service = CharacterService(repo)

        with pytest.raises(HTTPException) as exc_info:
            _ = await service.create(
                name="Alice",
                example_dialogues="invalid json {",
            )

        assert exc_info.value.status_code == 400
        assert "Invalid JSON" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_character_with_avatar(self, db: Session) -> None:
        """Test creating a character with avatar upload"""
        repo = CharacterRepository(db)
        service = CharacterService(repo)

        mock_file = Mock()
        mock_file.filename = "avatar.png"

        with patch(
            "src.character.service.save_character_avatar",
            new_callable=AsyncMock,
            return_value=(
                "avatars/char_123/avatar.png",
                "avatars/char_123/avatar_thumbnail.png",
            ),
        ):
            character = await service.create(
                name="Alice",
                avatar=mock_file,
            )

            assert character.avatar == "avatars/char_123/avatar.png"
            assert character.avatar_thumbnail == "avatars/char_123/avatar_thumbnail.png"

    @pytest.mark.asyncio
    async def test_update_character_basic_fields(self, db: Session) -> None:
        """Test updating character basic fields"""
        char = Character(name="Alice", description="Old description")
        db.add(char)
        db.commit()
        db.refresh(char)

        repo = CharacterRepository(db)
        service = CharacterService(repo)
        updated = await service.update(
            char.id,
            name="Alice Updated",
            description="New description",
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
        service = CharacterService(repo)
        updated = await service.update(char.id, description="Updated description")

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
        service = CharacterService(repo)
        greetings = json.dumps(["Hello!", "Hi!"])
        updated = await service.update(char.id, alternate_greetings=greetings)

        assert updated.alternate_greetings == ["Hello!", "Hi!"]

    @pytest.mark.asyncio
    async def test_update_character_not_found(self, db: Session) -> None:
        """Test updating non-existent character raises 404"""
        repo = CharacterRepository(db)
        service = CharacterService(repo)

        with pytest.raises(HTTPException) as exc_info:
            _ = await service.update("nonexistent-id", name="New Name")

        assert exc_info.value.status_code == 404

    def test_delete_character_success(self, db: Session) -> None:
        """Test deleting a character successfully"""
        char = Character(name="Alice")
        db.add(char)
        db.commit()
        db.refresh(char)
        char_id = char.id

        repo = CharacterRepository(db)
        service = CharacterService(repo)

        with patch("src.character.service.delete_character_files"):
            service.delete(char_id)

        # Verify character is deleted
        deleted = db.query(Character).filter(Character.id == char_id).first()
        assert deleted is None

    def test_delete_character_not_found(self, db: Session) -> None:
        """Test deleting non-existent character raises 404"""
        repo = CharacterRepository(db)
        service = CharacterService(repo)

        with pytest.raises(HTTPException) as exc_info:
            service.delete("nonexistent-id")

        assert exc_info.value.status_code == 404

    def test_parse_json_field_valid(self, db: Session) -> None:
        """Test JSON field parsing with valid JSON"""
        repo = CharacterRepository(db)
        service = CharacterService(repo)
        result = service._parse_json_field('{"key": "value"}', "test_field")  # pyright: ignore[reportPrivateUsage]
        assert result == {"key": "value"}

    def test_parse_json_field_none(self, db: Session) -> None:
        """Test JSON field parsing with None returns None"""
        repo = CharacterRepository(db)
        service = CharacterService(repo)
        result = service._parse_json_field(None, "test_field")  # pyright: ignore[reportPrivateUsage]
        assert result is None

    def test_parse_json_field_invalid(self, db: Session) -> None:
        """Test JSON field parsing with invalid JSON raises error"""
        repo = CharacterRepository(db)
        service = CharacterService(repo)

        with pytest.raises(HTTPException) as exc_info:
            _ = service._parse_json_field("invalid json", "test_field")  # pyright: ignore[reportPrivateUsage]

        assert exc_info.value.status_code == 400
        assert "test_field" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_import_card_json(self, db: Session) -> None:
        """Test importing a V2 JSON character card"""
        repo = CharacterRepository(db)
        service = CharacterService(repo)

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

        mock_file = Mock()
        mock_file.filename = "hero.json"
        mock_file.read = AsyncMock(return_value=v2_card.encode("utf-8"))

        character = await service.import_card(mock_file)

        assert character.name == "Imported Hero"
        assert character.description == "A brave adventurer"
        assert character.personality == "Bold and courageous"
        assert character.first_message == "Greetings, traveler!"
        assert character.scenario == "A fantasy world"
        assert character.system_prompt == "You are a brave hero."
        assert character.creator == "Tester"
        assert character.alternate_greetings == ["Hail!", "Welcome!"]
        assert character.tags == ["fantasy", "hero"]
        assert character.version == 2
        assert character.example_dialogues == ["<START>\nUser: Hello\nHero: Well met!"]

    def test_export_as_json(self, db: Session) -> None:
        """Test exporting a character as TavernCard V2 JSON"""
        char = Character(
            name="Export Test",
            description="A test character for export",
            personality="Friendly",
            first_message="Hello there!",
            scenario="Modern day",
            creator="Tester",
            alternate_greetings=["Hey!", "Hi!"],
            tags=["test"],
            example_dialogues=["<START>\nUser: Hi\nChar: Hello!"],
        )
        db.add(char)
        db.commit()
        db.refresh(char)

        repo = CharacterRepository(db)
        service = CharacterService(repo)
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
        assert "<START>" in data["mes_example"]

    @pytest.mark.asyncio
    async def test_import_and_export_character_book(self, db: Session) -> None:
        """Test importing and exporting a V2 JSON card with a character_book"""
        repo = CharacterRepository(db)
        service = CharacterService(repo)

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

        mock_file = Mock()
        mock_file.filename = "keeper.json"
        mock_file.read = AsyncMock(return_value=v2_card.encode("utf-8"))

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

    @pytest.mark.anyio
    async def test_import_and_export_custom_fields(self, db):
        from src.core.persistence.enums import Gender

        repo = CharacterRepository(db)
        service = CharacterService(repo)

        # 1. Test importing a card with species, age, gender in extensions
        v2_card = json.dumps(
            {
                "spec": "chara_card_v2",
                "spec_version": "2.0",
                "data": {
                    "name": "Custom Elf",
                    "extensions": {
                        "candlekeep": {
                            "species": "Altmer",
                            "gender": "female",
                            "age": "130",
                        }
                    },
                },
            }
        )

        mock_file = Mock()
        mock_file.filename = "elf.json"
        mock_file.read = AsyncMock(return_value=v2_card.encode("utf-8"))

        character = await service.import_card(mock_file)
        assert character.name == "Custom Elf"
        assert character.species == "Altmer"
        assert character.gender == Gender.FEMALE
        assert character.age == "130"

        # 2. Test exporting a character with custom fields
        db.refresh(character)
        json_str = service.export_as_json(character.id)
        exported = json.loads(json_str)

        assert exported["data"]["extensions"]["candlekeep"]["species"] == "Altmer"
        assert exported["data"]["extensions"]["candlekeep"]["gender"] == "female"
        assert exported["data"]["extensions"]["candlekeep"]["age"] == "130"
        assert exported["data"]["extensions"]["species"] == "Altmer"
        assert exported["data"]["extensions"]["gender"] == "female"
        assert exported["data"]["extensions"]["age"] == "130"
