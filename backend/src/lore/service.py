"""Lorebook business logic service"""

from src.core.exceptions import NotFoundError
from src.core.persistence.enums import InsertionPosition
from src.core.tokenization import get_tokenizer
from src.lore.activation_engine import ActivatedEntry, activate_entries
from src.lore.models import Lorebook, LoreEntry
from src.lore.repository import LoreEntryRepository, LoreRepository
from src.lore.schemas import LorebookCreate, LorebookUpdate, LoreEntryCreate, LoreEntryUpdate


class LoreService:
    """Service for lorebook and lore entry operations"""

    def __init__(
        self,
        lore_repo: LoreRepository,
        entry_repo: LoreEntryRepository,
    ):
        self.lore_repo = lore_repo
        self.entry_repo = entry_repo
        # Lore budgeting is family-agnostic (a rough size guard); a default
        # tokenizer is fine here.
        self.tokenizer = get_tokenizer(None)

    # --- Lorebook CRUD ---

    def list_lorebooks(
        self, character_id: str | None = None, is_global: bool | None = None
    ) -> list[Lorebook]:
        if character_id:
            return self.lore_repo.find_by_character_id(character_id)
        if is_global:
            return self.lore_repo.find_global()
        return self.lore_repo.find_all()

    def get_lorebook(self, lorebook_id: str) -> Lorebook:
        lorebook = self.lore_repo.find_by_id_with_entries(lorebook_id)
        if not lorebook:
            raise NotFoundError(f"Lorebook '{lorebook_id}' not found")
        return lorebook

    def create_lorebook(self, data: LorebookCreate) -> Lorebook:
        lorebook = Lorebook(
            name=data.name,
            description=data.description,
            is_global=data.is_global,
            character_id=data.character_id,
        )
        created = self.lore_repo.create(lorebook)
        self.lore_repo.commit()
        return created

    def update_lorebook(self, lorebook_id: str, data: LorebookUpdate) -> Lorebook:
        lorebook = self.get_lorebook(lorebook_id)
        if data.name is not None:
            lorebook.name = data.name
        if data.description is not None:
            lorebook.description = data.description
        if data.is_global is not None:
            lorebook.is_global = data.is_global
        updated = self.lore_repo.update(lorebook)
        self.lore_repo.commit()
        return updated

    def delete_lorebook(self, lorebook_id: str) -> None:
        lorebook = self.get_lorebook(lorebook_id)
        self.lore_repo.delete(lorebook)
        self.lore_repo.commit()

    # --- Entry CRUD ---

    def get_entry(self, lorebook_id: str, entry_id: str) -> LoreEntry:
        entry = self.entry_repo.find_by_id(entry_id)
        if not entry or entry.lorebook_id != lorebook_id:
            raise NotFoundError(f"Entry '{entry_id}' not found in lorebook '{lorebook_id}'")
        return entry

    def create_entry(self, lorebook_id: str, data: LoreEntryCreate) -> LoreEntry:
        self.get_lorebook(lorebook_id)
        entry = LoreEntry(
            lorebook_id=lorebook_id,
            name=data.name,
            content=data.content,
            keys=data.keys,
            secondary_keys=data.secondary_keys,
            secondary_logic=data.secondary_logic,
            case_sensitive=data.case_sensitive,
            match_whole_words=data.match_whole_words,
            use_regex=data.use_regex,
            enabled=data.enabled,
            constant=data.constant,
            position=data.position,
            depth=data.depth,
            role=data.role,
            priority=data.priority,
            scan_depth=data.scan_depth,
            ignore_budget=data.ignore_budget,
            order=data.order,
        )
        created = self.entry_repo.create(entry)
        self.entry_repo.commit()
        return created

    def update_entry(self, lorebook_id: str, entry_id: str, data: LoreEntryUpdate) -> LoreEntry:
        entry = self.get_entry(lorebook_id, entry_id)
        for field_name, value in data.model_dump(exclude_unset=True).items():
            setattr(entry, field_name, value)
        updated = self.entry_repo.update(entry)
        self.entry_repo.commit()
        return updated

    def delete_entry(self, lorebook_id: str, entry_id: str) -> None:
        entry = self.get_entry(lorebook_id, entry_id)
        self.entry_repo.delete(entry)
        self.entry_repo.commit()

    # --- Activation ---

    def get_activated_entries(
        self,
        character_id: str,
        scan_text: str,
        token_budget: int = 0,
    ) -> list[ActivatedEntry]:
        """
        Get all activated lore entries for a character's chat context.

        Collects entries from character-specific + global lorebooks,
        runs keyword activation, and enforces token budget.
        """
        lorebooks = self.lore_repo.find_for_character_with_entries(character_id)
        all_entries: list[LoreEntry] = []
        for lb in lorebooks:
            all_entries.extend(lb.entries)

        return activate_entries(all_entries, scan_text, token_budget, self.tokenizer)

    def get_entries_by_position(
        self,
        character_id: str,
        scan_text: str,
        token_budget: int = 0,
    ) -> dict[InsertionPosition, list[ActivatedEntry]]:
        """Get activated entries grouped by insertion position."""
        activated = self.get_activated_entries(character_id, scan_text, token_budget)
        grouped: dict[InsertionPosition, list[ActivatedEntry]] = {
            pos: [] for pos in InsertionPosition
        }
        for entry in activated:
            grouped[entry.position].append(entry)
        return grouped
