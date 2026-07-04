"""Character business logic service"""

import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile, status

from src.character.card_parser import (
    ParsedCard,
    export_card_json,
    export_card_png,
    parse_card_json,
    parse_card_png,
)
from src.character.models import Character
from src.character.repository import CharacterRepository
from src.core.persistence.enums import Gender
from src.core.utils.storage import delete_character_files, save_character_avatar


class CharacterService:
    """Service for character-related business logic"""

    def __init__(self, character_repo: CharacterRepository):
        self.character_repo = character_repo

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
        character = self.character_repo.find_by_id(character_id)
        if not character:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Character with ID '{character_id}' not found",
            )
        return character

    async def create(
        self,
        name: str,
        description: str | None = None,
        personality: str | None = None,
        first_message: str | None = None,
        example_dialogues: str | None = None,
        avatar: UploadFile | None = None,
        scenario: str | None = None,
        post_history_instructions: str | None = None,
        alternate_greetings: str | None = None,
        tags: str | None = None,
        gender: str | None = None,
        custom_gender: str | None = None,
        creator: str | None = None,
        version: int | None = 1,
        system_prompt: str | None = None,
        creator_notes: str | None = None,
        species: str | None = None,
        age: str | None = None,
    ) -> Character:
        """Create a new character with optional avatar upload"""
        parsed_dialogues = self._parse_json_field(example_dialogues, "example_dialogues")
        parsed_greetings = self._parse_json_field(alternate_greetings, "alternate_greetings")
        parsed_tags = self._parse_json_field(tags, "tags")

        # Parse gender enum
        parsed_gender = None
        if gender:
            try:
                parsed_gender = Gender(gender.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid gender value. Must be one of: {', '.join([g.value for g in Gender])}",
                ) from None

        character = Character(
            name=name,
            description=description,
            personality=personality,
            first_message=first_message,
            example_dialogues=parsed_dialogues,
            scenario=scenario,
            post_history_instructions=post_history_instructions,
            alternate_greetings=parsed_greetings,
            tags=parsed_tags,
            gender=parsed_gender,
            custom_gender=custom_gender,
            creator=creator,
            version=version or 1,
            system_prompt=system_prompt,
            creator_notes=creator_notes,
            species=species,
            age=age,
        )
        created = self.character_repo.create(character)

        if avatar:
            original_path, thumbnail_path = await save_character_avatar(created.id, avatar)
            created.avatar = original_path
            created.avatar_thumbnail = thumbnail_path
            _ = self.character_repo.update(created)

        self.character_repo.commit()
        return created

    async def update(
        self,
        character_id: str,
        name: str | None = None,
        description: str | None = None,
        personality: str | None = None,
        first_message: str | None = None,
        example_dialogues: str | None = None,
        avatar: UploadFile | None = None,
        scenario: str | None = None,
        post_history_instructions: str | None = None,
        alternate_greetings: str | None = None,
        tags: str | None = None,
        gender: str | None = None,
        custom_gender: str | None = None,
        creator: str | None = None,
        version: int | None = None,
        system_prompt: str | None = None,
        creator_notes: str | None = None,
        species: str | None = None,
        age: str | None = None,
    ) -> Character:
        """Update character"""
        character = self.get_by_id(character_id)

        if name is not None:
            character.name = name
        if description is not None:
            character.description = description
        if personality is not None:
            character.personality = personality
        if first_message is not None:
            character.first_message = first_message
        if scenario is not None:
            character.scenario = scenario
        if post_history_instructions is not None:
            character.post_history_instructions = post_history_instructions
        if gender is not None:
            try:
                character.gender = Gender(gender.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid gender value. Must be one of: {', '.join([g.value for g in Gender])}",
                ) from None
        if custom_gender is not None:
            character.custom_gender = custom_gender
        if creator is not None:
            character.creator = creator
        if version is not None:
            character.version = version
        if system_prompt is not None:
            character.system_prompt = system_prompt
        if creator_notes is not None:
            character.creator_notes = creator_notes
        if species is not None:
            character.species = species
        if age is not None:
            character.age = age

        # Parse and update JSON fields
        if example_dialogues is not None:
            character.example_dialogues = self._parse_json_field(
                example_dialogues, "example_dialogues"
            )
        if alternate_greetings is not None:
            character.alternate_greetings = self._parse_json_field(
                alternate_greetings, "alternate_greetings"
            )
        if tags is not None:
            character.tags = self._parse_json_field(tags, "tags")

        # Update avatar if provided
        if avatar:
            original_path, thumbnail_path = await save_character_avatar(character.id, avatar)
            character.avatar = original_path
            character.avatar_thumbnail = thumbnail_path

        updated = self.character_repo.update(character)
        self.character_repo.commit()
        return updated

    def delete(self, character_id: str) -> None:
        """Delete character and associated files"""
        character = self.get_by_id(character_id)

        # Delete character files
        delete_character_files(character_id)

        self.character_repo.delete(character)
        self.character_repo.commit()

    async def import_card(self, file: UploadFile) -> Character:
        """
        Import a character from a PNG or JSON card file.

        Supports TavernCard V1 and V2 formats, with PNG tEXt embedding or plain JSON.
        """
        file_data = await file.read()
        filename = (file.filename or "").lower()

        try:
            if filename.endswith(".png"):
                card = parse_card_png(file_data)
            elif filename.endswith(".json"):
                card = parse_card_json(file_data.decode("utf-8"))
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unsupported file format. Use .png or .json",
                )
        except (ValueError, json.JSONDecodeError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to parse character card: {e}",
            ) from e

        # Map example_dialogues: V2 stores as a single string, we store as list
        example_list = None
        if card.example_dialogues:
            example_list = [card.example_dialogues]

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
            version=2,
        )
        created = self.character_repo.create(character)

        # Create character_book if present in card
        if hasattr(card, "character_book") and card.character_book:
            from src.lore.repository import LoreRepository, LoreEntryRepository
            from src.lore.models import Lorebook, LoreEntry
            from src.core.persistence.enums import InsertionPosition, SecondaryLogic, MessageRole

            lore_repo = LoreRepository(self.character_repo.db)
            lore_entry_repo = LoreEntryRepository(self.character_repo.db)

            book_data = card.character_book
            lorebook = Lorebook(
                name=book_data.get("name") or f"{card.name} Lorebook",
                description=book_data.get("description"),
                is_global=False,
                character_id=created.id,
            )
            created_book = lore_repo.create(lorebook)

            # Map entries
            entries_data = book_data.get("entries", [])
            for idx, entry_dict in enumerate(entries_data):
                keys = entry_dict.get("keys", [])
                content = entry_dict.get("content", "")
                if not keys or not content:
                    continue

                # Map insertion position
                raw_pos = str(entry_dict.get("position", "after_character")).lower()
                position = InsertionPosition.AFTER_CHARACTER
                if "before_char" in raw_pos:
                    position = InsertionPosition.BEFORE_CHARACTER
                elif "after_char" in raw_pos:
                    position = InsertionPosition.AFTER_CHARACTER
                elif "depth" in raw_pos:
                    position = InsertionPosition.AT_DEPTH
                elif "example" in raw_pos:
                    position = InsertionPosition.BEFORE_EXAMPLES

                # Map secondary logic
                raw_logic = str(entry_dict.get("secondary_logic", "and_any")).lower()
                secondary_logic = SecondaryLogic.AND_ANY
                if "and_all" in raw_logic:
                    secondary_logic = SecondaryLogic.AND_ALL
                elif "not_any" in raw_logic:
                    secondary_logic = SecondaryLogic.NOT_ANY
                elif "not_all" in raw_logic:
                    secondary_logic = SecondaryLogic.NOT_ALL

                # Map role
                raw_role = str(entry_dict.get("role", "system")).lower()
                role = MessageRole.SYSTEM
                if "user" in raw_role:
                    role = MessageRole.USER
                elif "assistant" in raw_role or "char" in raw_role:
                    role = MessageRole.ASSISTANT

                lore_entry = LoreEntry(
                    lorebook_id=created_book.id,
                    name=entry_dict.get("name") or entry_dict.get("comment") or (keys[0] if keys else "Untitled"),
                    content=content,
                    keys=keys,
                    secondary_keys=entry_dict.get("secondary_keys", []),
                    secondary_logic=secondary_logic,
                    case_sensitive=entry_dict.get("case_sensitive", False),
                    match_whole_words=entry_dict.get("match_whole_words", False),
                    use_regex=entry_dict.get("use_regex", False),
                    enabled=entry_dict.get("enabled", True),
                    constant=entry_dict.get("constant", False),
                    position=position,
                    depth=entry_dict.get("depth", 4),
                    role=role,
                    priority=entry_dict.get("priority", 100),
                    ignore_budget=entry_dict.get("ignore_budget", False),
                    order=entry_dict.get("order", idx),
                )
                lore_entry_repo.create(lore_entry)

        # If PNG, use the file itself as avatar
        if filename.endswith(".png"):
            import io

            from fastapi import UploadFile as FUpload
            from starlette.datastructures import Headers

            avatar_file = FUpload(
                filename=f"{card.name}.png",
                file=io.BytesIO(file_data),
                headers=Headers({"content-type": "image/png"}),
            )
            original_path, thumbnail_path = await save_character_avatar(created.id, avatar_file)
            created.avatar = original_path
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
            from src.core.config import settings

            avatar_path = Path(settings.storage_path) / character.avatar
            if avatar_path.exists():
                avatar_data = avatar_path.read_bytes()

        return export_card_png(card, avatar_data)

    def _character_to_card(self, character: Character) -> ParsedCard:
        """Map a Character ORM instance to a ParsedCard for export."""
        example_str = ""
        if character.example_dialogues:
            example_str = "\n".join(character.example_dialogues)

        # Fetch character-specific lorebooks
        from sqlalchemy import select
        from sqlalchemy.orm import joinedload
        from src.lore.models import Lorebook

        stmt = (
            select(Lorebook)
            .where(Lorebook.character_id == character.id)
            .options(joinedload(Lorebook.entries))
        )
        lorebooks = list(self.character_repo.db.execute(stmt).scalars().unique().all())

        character_book = {}
        if lorebooks:
            lorebook = lorebooks[0]
            entries_data = []
            for entry in lorebook.entries:
                entries_data.append({
                    "keys": entry.keys,
                    "content": entry.content,
                    "constant": entry.constant,
                    "enabled": entry.enabled,
                    "name": entry.name,
                    "secondary_keys": entry.secondary_keys,
                    "case_sensitive": entry.case_sensitive,
                    "use_regex": entry.use_regex,
                    "match_whole_words": entry.match_whole_words,
                    "position": entry.position.value if hasattr(entry.position, "value") else str(entry.position),
                    "depth": entry.depth,
                    "role": entry.role.value if hasattr(entry.role, "value") else str(entry.role),
                    "priority": entry.priority,
                    "ignore_budget": entry.ignore_budget,
                    "order": entry.order,
                })
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
        )

    def _parse_json_field(self, value: str | None, field_name: str):
        """Parse JSON string field, raise 400 if invalid"""
        if value is None:
            return None

        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON format for {field_name}",
            ) from e
