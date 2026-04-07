"""Tests for LoreService CRUD operations"""

from typing import Any

import pytest
from sqlalchemy.orm import Session
from src.character import Character
from src.lore.models import LoreEntry
from src.lore.repository import LoreEntryRepository, LoreRepository
from src.lore.schemas import LorebookCreate, LoreEntryCreate
from src.lore.service import LoreService


@pytest.fixture
def sample_lorebook_character(db: Session) -> Character:
    char = Character(name="Lore Test Char", description="A test character")
    db.add(char)
    db.commit()
    db.refresh(char)
    return char


@pytest.fixture
def lore_service(db: Session) -> LoreService:
    return LoreService(LoreRepository(db), LoreEntryRepository(db))


class TestLoreService:
    def test_create_lorebook(
        self, lore_service: LoreService, sample_lorebook_character: Any
    ) -> None:
        data = LorebookCreate(
            name="World Lore",
            description="General world knowledge",
            character_id=sample_lorebook_character.id,
        )
        lorebook = lore_service.create_lorebook(data)

        assert lorebook.id is not None
        assert lorebook.name == "World Lore"
        assert lorebook.character_id == sample_lorebook_character.id

    def test_create_global_lorebook(self, lore_service: LoreService) -> None:
        data = LorebookCreate(name="Global Lore", is_global=True)
        lorebook = lore_service.create_lorebook(data)

        assert lorebook.is_global is True
        assert lorebook.character_id is None

    def test_create_entry(self, lore_service: LoreService, sample_lorebook_character: Any) -> None:
        lb = lore_service.create_lorebook(
            LorebookCreate(name="Test", character_id=sample_lorebook_character.id)
        )

        entry_data = LoreEntryCreate(
            name="Dragon Lore",
            content="Dragons are ancient creatures that breathe fire.",
            keys=["dragon", "wyrm"],
        )
        entry = lore_service.create_entry(lb.id, entry_data)

        assert entry.id is not None
        assert entry.name == "Dragon Lore"
        assert entry.keys == ["dragon", "wyrm"]
        assert entry.lorebook_id == lb.id

    def test_get_lorebook_with_entries(
        self, lore_service: LoreService, sample_lorebook_character: Any
    ) -> None:
        lb = lore_service.create_lorebook(
            LorebookCreate(name="Test", character_id=sample_lorebook_character.id)
        )
        lore_service.create_entry(
            lb.id, LoreEntryCreate(name="E1", content="Content 1", keys=["k1"])
        )
        lore_service.create_entry(
            lb.id, LoreEntryCreate(name="E2", content="Content 2", keys=["k2"])
        )

        result = lore_service.get_lorebook(lb.id)
        assert len(result.entries) == 2

    def test_get_activated_entries(
        self, lore_service: LoreService, sample_lorebook_character: Any
    ) -> None:
        lb = lore_service.create_lorebook(
            LorebookCreate(name="Test", character_id=sample_lorebook_character.id)
        )
        lore_service.create_entry(
            lb.id, LoreEntryCreate(name="Dragon", content="Fire breathing", keys=["dragon"])
        )
        lore_service.create_entry(
            lb.id, LoreEntryCreate(name="Elf", content="Pointy ears", keys=["elf"])
        )

        result = lore_service.get_activated_entries(
            character_id=sample_lorebook_character.id,
            scan_text="I see a dragon in the distance",
        )

        assert len(result) == 1
        assert result[0].content == "Fire breathing"

    def test_delete_lorebook_cascades(
        self, db: Session, lore_service: LoreService, sample_lorebook_character: Any
    ) -> None:
        lb = lore_service.create_lorebook(
            LorebookCreate(name="Del Test", character_id=sample_lorebook_character.id)
        )
        lore_service.create_entry(lb.id, LoreEntryCreate(name="E1", content="Content", keys=["k1"]))

        lore_service.delete_lorebook(lb.id)

        from sqlalchemy import select

        entries = db.execute(select(LoreEntry)).scalars().all()
        assert len(entries) == 0
