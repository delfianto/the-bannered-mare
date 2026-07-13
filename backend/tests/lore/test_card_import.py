"""Tests for TavernCard character_book -> lore ORM mapping (network-free)."""

import pytest
from src.core.persistence.enums import InsertionPosition, MessageRole, SecondaryLogic
from src.lore.card_import import build_lorebook, map_lore_entry


def _entry(**overrides) -> dict:
    base = {"keys": ["dragon"], "content": "Dragons breathe fire"}
    base.update(overrides)
    return base


class TestBuildLorebook:
    def test_uses_card_name_and_description(self) -> None:
        book = build_lorebook({"name": "Realm", "description": "Lore"}, "char1", "Alice")
        assert book.name == "Realm"
        assert book.description == "Lore"
        assert book.character_id == "char1"
        assert book.is_global is False

    def test_falls_back_to_character_name(self) -> None:
        book = build_lorebook({}, "char1", "Alice")
        assert book.name == "Alice Lorebook"


class TestMapLoreEntrySkips:
    def test_none_when_no_keys(self) -> None:
        assert map_lore_entry({"keys": [], "content": "x"}, "book1", 0) is None

    def test_none_when_no_content(self) -> None:
        assert map_lore_entry({"keys": ["k"], "content": ""}, "book1", 0) is None


class TestMapLoreEntryEnums:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("before_character", InsertionPosition.BEFORE_CHARACTER),
            ("before_char", InsertionPosition.BEFORE_CHARACTER),
            ("after_character", InsertionPosition.AFTER_CHARACTER),
            ("at_depth", InsertionPosition.AT_DEPTH),
            ("before_examples", InsertionPosition.BEFORE_EXAMPLES),
            ("something_unknown", InsertionPosition.AFTER_CHARACTER),  # default
        ],
    )
    def test_position(self, raw: str, expected: InsertionPosition) -> None:
        entry = map_lore_entry(_entry(position=raw), "book1", 0)
        assert entry is not None and entry.position == expected

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("and_all", SecondaryLogic.AND_ALL),
            ("not_any", SecondaryLogic.NOT_ANY),
            ("not_all", SecondaryLogic.NOT_ALL),
            ("and_any", SecondaryLogic.AND_ANY),  # default
            ("whatever", SecondaryLogic.AND_ANY),  # default
        ],
    )
    def test_secondary_logic(self, raw: str, expected: SecondaryLogic) -> None:
        entry = map_lore_entry(_entry(secondary_logic=raw), "book1", 0)
        assert entry is not None and entry.secondary_logic == expected

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("user", MessageRole.USER),
            ("assistant", MessageRole.ASSISTANT),
            ("char", MessageRole.ASSISTANT),
            ("system", MessageRole.SYSTEM),  # default
            ("", MessageRole.SYSTEM),  # default
        ],
    )
    def test_role(self, raw: str, expected: MessageRole) -> None:
        entry = map_lore_entry(_entry(role=raw), "book1", 0)
        assert entry is not None and entry.role == expected


class TestMapLoreEntryFields:
    def test_defaults_and_name_fallback(self) -> None:
        entry = map_lore_entry({"keys": ["k1", "k2"], "content": "c"}, "book1", 7)
        assert entry is not None
        assert entry.lorebook_id == "book1"
        assert entry.name == "k1"  # falls back to first key
        assert entry.depth == 4
        assert entry.priority == 100
        assert entry.order == 7  # falls back to the enumerate index

    def test_explicit_order_wins_over_index(self) -> None:
        entry = map_lore_entry(_entry(order=3), "book1", 99)
        assert entry is not None and entry.order == 3
