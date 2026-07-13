"""Map a TavernCard ``character_book`` into lore ORM objects.

Kept in the lore domain (it constructs Lorebook/LoreEntry) and out of
CharacterService.import_card, which only orchestrates. The card's position/
secondary-logic/role values vary across exporters ("before_char" vs
"before_character", etc.), so each is matched leniently against a recognizable
token with a sane default — expressed as data (a dict) rather than an if-ladder.
"""

from enum import Enum
from typing import Any

from src.core.persistence.enums import InsertionPosition, MessageRole, SecondaryLogic
from src.lore.models import Lorebook, LoreEntry

_DEFAULT_DEPTH = 4
_DEFAULT_PRIORITY = 100

# Substring token -> enum; first match wins (insertion order).
_POSITION_TOKENS: dict[str, InsertionPosition] = {
    "before_char": InsertionPosition.BEFORE_CHARACTER,
    "after_char": InsertionPosition.AFTER_CHARACTER,
    "depth": InsertionPosition.AT_DEPTH,
    "example": InsertionPosition.BEFORE_EXAMPLES,
}
_LOGIC_TOKENS: dict[str, SecondaryLogic] = {
    "and_all": SecondaryLogic.AND_ALL,
    "not_any": SecondaryLogic.NOT_ANY,
    "not_all": SecondaryLogic.NOT_ALL,
}
_ROLE_TOKENS: dict[str, MessageRole] = {
    "user": MessageRole.USER,
    "assistant": MessageRole.ASSISTANT,
    "char": MessageRole.ASSISTANT,
}


def _match_token[E: Enum](raw: object, tokens: dict[str, E], default: E) -> E:
    """First mapping value whose token is a substring of ``str(raw).lower()``, else default."""
    text = str(raw).lower()
    for token, value in tokens.items():
        if token in text:
            return value
    return default


def build_lorebook(book_data: dict[str, Any], character_id: str, fallback_name: str) -> Lorebook:
    """Build the (unpersisted) Lorebook for an imported character card."""
    return Lorebook(
        name=book_data.get("name") or f"{fallback_name} Lorebook",
        description=book_data.get("description"),
        is_global=False,
        character_id=character_id,
    )


def map_lore_entry(entry_dict: dict[str, Any], lorebook_id: str, order: int) -> LoreEntry | None:
    """Map one card ``character_book`` entry to a LoreEntry.

    Returns None for entries with no keys or no content (nothing to activate on).
    """
    keys = entry_dict.get("keys", [])
    content = entry_dict.get("content", "")
    if not keys or not content:
        return None

    return LoreEntry(
        lorebook_id=lorebook_id,
        name=entry_dict.get("name")
        or entry_dict.get("comment")
        or (keys[0] if keys else "Untitled"),
        content=content,
        keys=keys,
        secondary_keys=entry_dict.get("secondary_keys", []),
        secondary_logic=_match_token(
            entry_dict.get("secondary_logic", "and_any"), _LOGIC_TOKENS, SecondaryLogic.AND_ANY
        ),
        case_sensitive=entry_dict.get("case_sensitive", False),
        match_whole_words=entry_dict.get("match_whole_words", False),
        use_regex=entry_dict.get("use_regex", False),
        enabled=entry_dict.get("enabled", True),
        constant=entry_dict.get("constant", False),
        position=_match_token(
            entry_dict.get("position", "after_character"),
            _POSITION_TOKENS,
            InsertionPosition.AFTER_CHARACTER,
        ),
        depth=entry_dict.get("depth", _DEFAULT_DEPTH),
        role=_match_token(entry_dict.get("role", "system"), _ROLE_TOKENS, MessageRole.SYSTEM),
        priority=entry_dict.get("priority", _DEFAULT_PRIORITY),
        ignore_budget=entry_dict.get("ignore_budget", False),
        order=entry_dict.get("order", order),
    )
