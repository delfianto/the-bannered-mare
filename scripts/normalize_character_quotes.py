#!/usr/bin/env python3
"""Backfill: fold Unicode "smart" quotes to ASCII on existing character rows.

New imports are normalized automatically (see
``src.character.card_parser.normalize_card_quotes``); this is a one-off fixup
for rows that were imported before that existed. Prints a per-field diff and,
by default, only previews -- pass --apply to write the changes.

Run with the backend virtualenv; needs the backend env (.env / DATABASE_URL):

    backend/.venv/bin/python scripts/normalize_character_quotes.py            # preview
    backend/.venv/bin/python scripts/normalize_character_quotes.py --apply    # write
"""

import argparse
import os
import sys

# Backend lives one level up from this repo-root scripts/ folder.
_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, _BACKEND)

from src.character.card_parser import normalize_smart_quotes
from src.character.repository import CharacterRepository
from src.core.persistence.database import get_db

_TEXT_FIELDS = [
    "name",
    "description",
    "personality",
    "first_message",
    "scenario",
    "post_history_instructions",
    "system_prompt",
    "creator_notes",
    "species",
    "age",
    "character_version",
    "creator",
    "custom_gender",
]
_LIST_FIELDS = ["example_dialogues", "alternate_greetings", "tags"]


def _snippet(text: str, around: int = 30) -> str:
    """Short preview for diff output; collapses newlines so it stays one line."""
    flat = " ".join(text.split())
    return flat if len(flat) <= around * 2 else f"{flat[:around]}…{flat[-around:]}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write changes (default: preview only)")
    args = parser.parse_args()

    db = next(get_db())
    repo = CharacterRepository(db)

    changed_rows = 0
    changed_fields = 0
    for character in repo.find_all():
        row_changed = False
        for name in _TEXT_FIELDS:
            value = getattr(character, name)
            if not value:
                continue
            normalized = normalize_smart_quotes(value)
            if normalized != value:
                print(f"{character.name!r} .{name}: {_snippet(value)!r} -> {_snippet(normalized)!r}")
                setattr(character, name, normalized)
                row_changed = True
                changed_fields += 1

        for name in _LIST_FIELDS:
            values = getattr(character, name)
            if not values:
                continue
            normalized_list = [normalize_smart_quotes(v) for v in values]
            if normalized_list != values:
                for old, new in zip(values, normalized_list, strict=True):
                    if old != new:
                        print(f"{character.name!r} .{name}[]: {_snippet(old)!r} -> {_snippet(new)!r}")
                setattr(character, name, normalized_list)
                row_changed = True
                changed_fields += 1

        if row_changed:
            changed_rows += 1
            if args.apply:
                repo.update(character)

    if args.apply:
        db.commit()
        print(f"\nApplied: {changed_fields} field(s) across {changed_rows} character(s).")
    else:
        print(f"\nPreview only: {changed_fields} field(s) across {changed_rows} character(s) would change.")
        print("Re-run with --apply to write.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
