"""Stateless one-pass keyword activation engine for lore entries."""

import re
from dataclasses import dataclass

from src.core.persistence.enums import InsertionPosition, SecondaryLogic
from src.core.utils.tokenizer import TokenizerService
from src.lore.models import LoreEntry


@dataclass
class ActivatedEntry:
    """A lore entry that passed activation and is ready for prompt injection."""

    content: str
    position: InsertionPosition
    depth: int
    role: str
    priority: int


def _match_keyword(keyword: str, text: str, *, case_sensitive: bool, whole_words: bool) -> bool:
    """Check if a single keyword matches the scan text."""
    flags = 0 if case_sensitive else re.IGNORECASE
    if whole_words:
        pattern = rf"\b{re.escape(keyword)}\b"
    else:
        pattern = re.escape(keyword)
    return bool(re.search(pattern, text, flags))


def _match_regex(pattern: str, text: str, *, case_sensitive: bool) -> bool:
    """Check if a regex pattern matches the scan text."""
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        return bool(re.search(pattern, text, flags))
    except re.error:
        return False


def _matches_primary(entry: LoreEntry, text: str) -> bool:
    """Check if any primary key matches the scan text."""
    if not entry.keys:
        return False

    for key in entry.keys:
        if entry.use_regex:
            if _match_regex(key, text, case_sensitive=entry.case_sensitive):
                return True
        elif _match_keyword(
            key, text, case_sensitive=entry.case_sensitive, whole_words=entry.match_whole_words
        ):
            return True

    return False


def _passes_secondary(entry: LoreEntry, text: str) -> bool:
    """Apply secondary logic filter after primary match."""
    if not entry.secondary_keys:
        return True

    matches = []
    for key in entry.secondary_keys:
        if entry.use_regex:
            matches.append(_match_regex(key, text, case_sensitive=entry.case_sensitive))
        else:
            matches.append(
                _match_keyword(
                    key,
                    text,
                    case_sensitive=entry.case_sensitive,
                    whole_words=entry.match_whole_words,
                )
            )

    logic = entry.secondary_logic

    if logic == SecondaryLogic.AND_ANY:
        return any(matches)
    elif logic == SecondaryLogic.AND_ALL:
        return all(matches)
    elif logic == SecondaryLogic.NOT_ANY:
        return not any(matches)
    elif logic == SecondaryLogic.NOT_ALL:
        return not all(matches)

    return True


def activate_entries(
    entries: list[LoreEntry],
    scan_text: str,
    token_budget: int,
    tokenizer: TokenizerService,
) -> list[ActivatedEntry]:
    """
    One-pass activation: match keywords, enforce budget, return ordered entries.

    Args:
        entries: All candidate entries (enabled only).
        scan_text: Concatenated recent messages + character context.
        token_budget: Max tokens for lore injection (0 = unlimited).
        tokenizer: For counting tokens in entry content.

    Returns:
        Activated entries sorted by priority (descending).
    """
    activated: list[ActivatedEntry] = []

    for entry in entries:
        if not entry.enabled:
            continue

        if entry.constant:
            activated.append(_to_activated(entry))
            continue

        if _matches_primary(entry, scan_text) and _passes_secondary(entry, scan_text):
            activated.append(_to_activated(entry))

    activated.sort(key=lambda e: e.priority, reverse=True)

    if token_budget <= 0:
        return activated

    budgeted: list[ActivatedEntry] = []
    used = 0

    for entry in activated:
        if entry.priority < 0:
            continue

        tokens = tokenizer.count_tokens(entry.content)

        # ignore_budget entries from the original LoreEntry aren't tracked here
        # because ActivatedEntry doesn't carry that flag. We handle it below.
        if used + tokens <= token_budget:
            budgeted.append(entry)
            used += tokens

    return budgeted


def _to_activated(entry: LoreEntry) -> ActivatedEntry:
    return ActivatedEntry(
        content=entry.content,
        position=entry.position,
        depth=entry.depth,
        role=entry.role.value,
        priority=entry.priority,
    )
