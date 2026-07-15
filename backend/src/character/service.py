"""Character business logic service"""

import json
from pathlib import Path
from typing import Any

from anyio import to_thread

from src.character.card_parser import (
    ParsedCard,
    export_card_json,
    export_card_png,
    parse_card_json,
    parse_card_png,
    split_example_dialogues,
)
from src.character.models import Character
from src.character.repository import CharacterRepository
from src.character.schemas import CharacterFormBase
from src.core.base_service import get_or_404
from src.core.config import settings
from src.core.exceptions import ValidationError
from src.core.logging import get_logger
from src.core.persistence.enums import Gender
from src.core.utils.storage import delete_character_files, save_character_avatar
from src.core.utils.upload import UploadedFile
from src.lore.card_import import build_lorebook, map_lore_entry
from src.lore.repository import LoreEntryRepository, LoreRepository

logger = get_logger(__name__)


def _parse_gender(value: str) -> Gender:
    """Parse a gender string to the enum, or raise 400 (create/update path)."""
    try:
        return Gender(value.lower())
    except ValueError:
        raise ValidationError(
            f"Invalid gender value. Must be one of: {', '.join(g.value for g in Gender)}"
        ) from None


class CharacterService:
    """Service for character-related business logic"""

    def __init__(
        self,
        character_repo: CharacterRepository,
        lore_repo: LoreRepository,
        lore_entry_repo: LoreEntryRepository,
    ):
        self.character_repo = character_repo
        # Character import/export reads & writes the character's lorebook. The lore
        # repositories are injected on the same session, so the import stays one
        # transaction.
        self.lore_repo = lore_repo
        self.lore_entry_repo = lore_entry_repo

    def list_all(self) -> list[Character]:
        """List all characters"""
        return self.character_repo.find_all_ordered()

    def list_paginated(
        self, limit: int = 10, offset: int = 0, filters: dict[str, Any] | None = None
    ) -> tuple[list[Character], int]:
        """List characters with pagination and filtering"""
        return self.character_repo.find_paginated_ordered(limit, offset, filters)

    def get_by_id(self, character_id: str) -> Character:
        """Get character by ID, raise 404 if not found"""
        return get_or_404(self.character_repo, character_id, "Character")

    async def create(
        self, data: CharacterFormBase, avatar: UploadedFile | None = None
    ) -> Character:
        """Create a new character with optional avatar upload"""
        if not data.name:
            raise ValidationError("Character name is required")

        parsed_dialogues = self._parse_json_field(data.example_dialogues, "example_dialogues")
        parsed_greetings = self._parse_json_field(data.alternate_greetings, "alternate_greetings")
        parsed_tags = self._parse_json_field(data.tags, "tags")

        parsed_gender = _parse_gender(data.gender) if data.gender else None

        character = Character(
            name=data.name,
            description=data.description,
            personality=data.personality,
            first_message=data.first_message,
            example_dialogues=parsed_dialogues,
            scenario=data.scenario,
            post_history_instructions=data.post_history_instructions,
            alternate_greetings=parsed_greetings,
            tags=parsed_tags,
            gender=parsed_gender,
            custom_gender=data.custom_gender,
            creator=data.creator,
            version=data.version or 1,
            system_prompt=data.system_prompt,
            creator_notes=data.creator_notes,
            species=data.species,
            age=data.age,
        )
        created = self.character_repo.create(character)

        if avatar:
            original_path, large_path, thumbnail_path = await save_character_avatar(
                created.id, avatar
            )
            created.avatar = original_path
            created.avatar_large = large_path
            created.avatar_thumbnail = thumbnail_path
            _ = self.character_repo.update(created)

        self.character_repo.commit()
        return created

    async def update(
        self,
        character_id: str,
        data: CharacterFormBase,
        avatar: UploadedFile | None = None,
    ) -> Character:
        """Update character"""
        character = self.get_by_id(character_id)

        if data.name is not None:
            character.name = data.name
        if data.description is not None:
            character.description = data.description
        if data.personality is not None:
            character.personality = data.personality
        if data.first_message is not None:
            character.first_message = data.first_message
        if data.scenario is not None:
            character.scenario = data.scenario
        if data.post_history_instructions is not None:
            character.post_history_instructions = data.post_history_instructions
        if data.gender is not None:
            character.gender = _parse_gender(data.gender)
        if data.custom_gender is not None:
            character.custom_gender = data.custom_gender
        if data.creator is not None:
            character.creator = data.creator
        if data.version is not None:
            character.version = data.version
        if data.system_prompt is not None:
            character.system_prompt = data.system_prompt
        if data.creator_notes is not None:
            character.creator_notes = data.creator_notes
        if data.species is not None:
            character.species = data.species
        if data.age is not None:
            character.age = data.age

        if data.example_dialogues is not None:
            character.example_dialogues = self._parse_json_field(
                data.example_dialogues, "example_dialogues"
            )
        if data.alternate_greetings is not None:
            character.alternate_greetings = self._parse_json_field(
                data.alternate_greetings, "alternate_greetings"
            )
        if data.tags is not None:
            character.tags = self._parse_json_field(data.tags, "tags")

        if avatar:
            original_path, large_path, thumbnail_path = await save_character_avatar(
                character.id, avatar
            )
            character.avatar = original_path
            character.avatar_large = large_path
            character.avatar_thumbnail = thumbnail_path

        updated = self.character_repo.update(character)
        self.character_repo.commit()
        return updated

    def delete(self, character_id: str) -> None:
        """Delete character and associated files"""
        character = self.get_by_id(character_id)

        delete_character_files(character_id)

        self.character_repo.delete(character)
        self.character_repo.commit()

    async def import_card(self, upload: UploadedFile) -> Character:
        """
        Import a character from a PNG or JSON card file.

        Supports TavernCard V1 and V2 formats, with PNG tEXt embedding or plain JSON.
        """
        file_data = upload.data
        filename = upload.filename.lower()

        try:
            if filename.endswith(".png"):
                # PNG decode + tEXt extraction is CPU-bound — off the event loop.
                card = await to_thread.run_sync(parse_card_png, file_data)
            elif filename.endswith(".json"):
                card = parse_card_json(file_data.decode("utf-8"))
            else:
                raise ValidationError("Unsupported file format. Use .png or .json")
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning("card_parse_failed", filename=filename, error=str(e))
            raise ValidationError(
                "Failed to parse character card: unsupported or corrupt file."
            ) from e

        # Map example_dialogues: cards store one freeform mes_example string with
        # <START>-delimited blocks — store one entry per block, dropping empties,
        # rather than dumping the whole thing into a single giant "example".
        blocks = split_example_dialogues(card.example_dialogues)
        example_list = blocks or None

        # Map gender string to Gender enum or OTHERS
        gender_enum = None
        custom_gender = None
        if card.gender:
            g_str = card.gender.lower().strip()
            if g_str in ["male", "female", "non-binary"]:
                if g_str == "male":
                    gender_enum = Gender.MALE
                elif g_str == "female":
                    gender_enum = Gender.FEMALE
                elif g_str == "non-binary":
                    gender_enum = Gender.NON_BINARY
            else:
                gender_enum = Gender.OTHERS
                custom_gender = card.gender
        elif card.custom_gender:
            gender_enum = Gender.OTHERS
            custom_gender = card.custom_gender

        character = Character(
            name=card.name,
            description=card.description or None,
            personality=card.personality or None,
            first_message=card.first_message or None,
            example_dialogues=example_list,
            scenario=card.scenario or None,
            system_prompt=card.system_prompt or None,
            post_history_instructions=card.post_history_instructions or None,
            creator_notes=card.creator_notes or None,
            creator=card.creator or None,
            character_version=card.character_version or None,
            alternate_greetings=card.alternate_greetings or None,
            tags=card.tags or None,
            species=card.species or None,
            age=card.age or None,
            gender=gender_enum,
            custom_gender=custom_gender,
            version=2,
        )
        created = self.character_repo.create(character)

        # Build the character's lorebook from the card, if present.
        if card.character_book:
            created_book = self.lore_repo.create(
                build_lorebook(card.character_book, created.id, card.name)
            )
            for idx, entry_dict in enumerate(card.character_book.get("entries", [])):
                entry = map_lore_entry(entry_dict, created_book.id, idx)
                if entry is not None:
                    self.lore_entry_repo.create(entry)

        # If PNG, use the file itself as avatar
        if filename.endswith(".png"):
            original_path, large_path, thumbnail_path = await save_character_avatar(
                created.id, UploadedFile(file_data, f"{card.name}.png")
            )
            created.avatar = original_path
            created.avatar_large = large_path
            created.avatar_thumbnail = thumbnail_path
            _ = self.character_repo.update(created)

        self.character_repo.commit()
        return created

    def export_as_json(self, character_id: str) -> str:
        """Export a character as TavernCard V2 JSON."""
        character = self.get_by_id(character_id)
        card = self._character_to_card(character)
        return export_card_json(card)

    def export_as_png(self, character_id: str) -> bytes:
        """Export a character as PNG with embedded V2 JSON in tEXt chunk."""
        character = self.get_by_id(character_id)
        card = self._character_to_card(character)

        avatar_data = None
        if character.avatar:
            avatar_path = Path(settings.storage_path) / character.avatar
            if avatar_path.exists():
                avatar_data = avatar_path.read_bytes()

        return export_card_png(card, avatar_data)

    def _character_to_card(self, character: Character) -> ParsedCard:
        """Map a Character ORM instance to a ParsedCard for export."""
        example_str = ""
        if character.example_dialogues:
            example_str = "\n".join(character.example_dialogues)

        # Fetch character-specific lorebooks (via the lore repository, not raw SQL
        # on the character session).
        lorebooks = self.lore_repo.find_for_character_with_entries(character.id)

        character_book = {}
        if lorebooks:
            lorebook = lorebooks[0]
            entries_data = []
            for entry in lorebook.entries:
                entries_data.append(
                    {
                        "keys": entry.keys,
                        "content": entry.content,
                        "constant": entry.constant,
                        "enabled": entry.enabled,
                        "name": entry.name,
                        "secondary_keys": entry.secondary_keys,
                        "case_sensitive": entry.case_sensitive,
                        "use_regex": entry.use_regex,
                        "match_whole_words": entry.match_whole_words,
                        "position": entry.position.value
                        if hasattr(entry.position, "value")
                        else str(entry.position),
                        "depth": entry.depth,
                        "role": entry.role.value
                        if hasattr(entry.role, "value")
                        else str(entry.role),
                        "priority": entry.priority,
                        "ignore_budget": entry.ignore_budget,
                        "order": entry.order,
                    }
                )
            character_book = {
                "name": lorebook.name,
                "description": lorebook.description or "",
                "entries": entries_data,
            }

        return ParsedCard(
            name=character.name,
            description=character.description or "",
            personality=character.personality or "",
            first_message=character.first_message or "",
            example_dialogues=example_str,
            scenario=character.scenario or "",
            system_prompt=character.system_prompt or "",
            post_history_instructions=character.post_history_instructions or "",
            creator_notes=character.creator_notes or "",
            creator=character.creator or "",
            character_version=character.character_version or "",
            alternate_greetings=character.alternate_greetings or [],
            tags=character.tags or [],
            character_book=character_book,
            species=character.species or "",
            gender=character.gender.value if character.gender else "",
            custom_gender=character.custom_gender or "",
            age=character.age or "",
        )

    def _parse_json_field(self, value: str | None, field_name: str):
        """Parse JSON string field, raise 400 if invalid"""
        if value is None:
            return None

        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON format for {field_name}") from e
