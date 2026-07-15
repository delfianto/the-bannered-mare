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
from src.core.persistence import UnitOfWork
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


def _map_card_gender(
    gender: str | None, custom_gender: str | None
) -> tuple[Gender | None, str | None]:
    """Resolve a card's gender / custom_gender strings to ``(Gender, custom_gender)``.

    Recognized values (male / female / non-binary) map to their enum member via the
    same lookup as the create/update path (``_parse_gender``). Anything else — an
    unknown label, or a card that only carries a free-text ``custom_gender`` —
    becomes ``Gender.OTHERS`` with the original string kept as the custom label.
    Unlike the create/update path this never raises: an unmapped card gender is
    stored as a custom gender, not rejected.
    """
    if gender:
        try:
            parsed = _parse_gender(gender.strip())
        except ValidationError:
            parsed = Gender.OTHERS
        if parsed is not Gender.OTHERS:
            return parsed, None
        return Gender.OTHERS, gender
    if custom_gender:
        return Gender.OTHERS, custom_gender
    return None, None


def _build_character_from_card(card: ParsedCard) -> Character:
    """Construct an (unsaved) Character ORM instance from a parsed card."""
    # Cards store one freeform mes_example string with <START>-delimited blocks —
    # store one entry per block, dropping empties, rather than one giant "example".
    example_list = split_example_dialogues(card.example_dialogues) or None
    gender_enum, custom_gender = _map_card_gender(card.gender, card.custom_gender)

    return Character(
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


class CharacterService:
    """Service for character-related business logic"""

    def __init__(
        self,
        character_repo: CharacterRepository,
        lore_repo: LoreRepository,
        lore_entry_repo: LoreEntryRepository,
        uow: UnitOfWork | None = None,
    ):
        self.character_repo = character_repo
        # Character import/export reads & writes the character's lorebook. The lore
        # repositories are injected on the same session, so the import stays one
        # transaction.
        self.lore_repo = lore_repo
        self.lore_entry_repo = lore_entry_repo
        # The unit of work owns the transaction boundary; it wraps the same session
        # the repos share. Fallback keeps direct `CharacterService(...)` construction
        # (tests) valid — the DI factory injects the request-scoped UoW.
        self.uow = uow or UnitOfWork(character_repo.db)

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

        # The avatar's stored paths must be persisted on the row, so the file has to
        # be written before commit; ``_commit_or_purge_avatar_files`` reverses the
        # exposure by removing those files if the commit then fails.
        avatar_written = False
        if avatar:
            original_path, large_path, thumbnail_path = await save_character_avatar(
                created.id, avatar
            )
            created.avatar = original_path
            created.avatar_large = large_path
            created.avatar_thumbnail = thumbnail_path
            _ = self.character_repo.update(created)
            avatar_written = True

        self._commit_or_purge_avatar_files(created.id, wrote_avatar=avatar_written)
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
        self.uow.commit()
        return updated

    def delete(self, character_id: str) -> None:
        """Delete character and associated files"""
        character = self.get_by_id(character_id)

        self.character_repo.delete(character)
        self.uow.commit()

        # Filesystem after the DB: remove the avatar files only once the delete has
        # committed, so a failed commit can't strand a fileless entity.
        delete_character_files(character_id)

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

        created = self.character_repo.create(_build_character_from_card(card))
        self._import_character_book(card, created)
        # PNG imports write the uploaded file as the avatar before commit (its paths
        # land on the row); purge it if the commit fails so nothing is orphaned.
        wrote_avatar = await self._maybe_set_png_avatar(created, file_data, filename, card.name)

        self._commit_or_purge_avatar_files(created.id, wrote_avatar=wrote_avatar)
        return created

    def _commit_or_purge_avatar_files(self, character_id: str, *, wrote_avatar: bool) -> None:
        """Commit the pending character transaction, ordering the filesystem after the DB.

        ``create``/``import_card`` must write the avatar to disk *before* commit
        because the derived paths are persisted on the row. If that commit then
        fails the row is rolled back, so any avatar files just written (keyed by the
        character id) are removed before the error propagates — a rolled-back
        create/import leaves nothing orphaned on disk. A failure of the cleanup
        itself is logged and swallowed so the original commit error still surfaces.
        """
        try:
            self.uow.commit()
        except Exception:
            if wrote_avatar:
                try:
                    delete_character_files(character_id)
                except Exception:
                    logger.warning(
                        "avatar_cleanup_after_failed_commit_failed",
                        character_id=character_id,
                        exc_info=True,
                    )
            raise

    def _import_character_book(self, card: ParsedCard, character: Character) -> None:
        """Build and persist the imported character's lorebook from the card, if any."""
        if not card.character_book:
            return

        created_book = self.lore_repo.create(
            build_lorebook(card.character_book, character.id, card.name)
        )
        for idx, entry_dict in enumerate(card.character_book.get("entries", [])):
            entry = map_lore_entry(entry_dict, created_book.id, idx)
            if entry is not None:
                self.lore_entry_repo.create(entry)

    async def _maybe_set_png_avatar(
        self, character: Character, file_data: bytes, filename: str, card_name: str
    ) -> bool:
        """For PNG imports, reuse the uploaded file itself as the character's avatar.

        Returns ``True`` when avatar files were written to disk (PNG imports only),
        so the caller can purge them if the ensuing commit fails.
        """
        if not filename.endswith(".png"):
            return False

        original_path, large_path, thumbnail_path = await save_character_avatar(
            character.id, UploadedFile(file_data, f"{card_name}.png")
        )
        character.avatar = original_path
        character.avatar_large = large_path
        character.avatar_thumbnail = thumbnail_path
        _ = self.character_repo.update(character)
        return True

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
                        "position": entry.position.value,
                        "depth": entry.depth,
                        "role": entry.role.value,
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
