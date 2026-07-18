#!/usr/bin/env python3
"""Backfill: rewrite bullet-listed description/personality into blank-line prose.

New imports are normalized automatically (see
``src.character.card_parser.normalize_card_bullets``); this is a one-off fixup for
rows imported before that existed -- notably cards whose bullet lists were flattened
into runs of spaces ("...her.       - Daydreamer: ..."). Each bulleted field becomes
one paragraph per item, marker dropped, blank line between. Only fields that *start*
with a bullet marker change. Prints a per-field diff and, by default, only previews --
pass --apply to write.

Run with the backend virtualenv; needs the backend env (.env / DATABASE_URL):

    backend/.venv/bin/python scripts/normalize_character_bullets.py            # preview
    backend/.venv/bin/python scripts/normalize_character_bullets.py --apply    # write
"""

import argparse
import os
import sys

# Backend lives one level up from this repo-root scripts/ folder.
_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, _BACKEND)

from src.character.card_parser import normalize_bullet_list
from src.character.repository import CharacterRepository
from src.core.persistence.database import get_db

_BULLET_LIST_FIELDS = ["description", "personality"]


def _snippet(text: str, around: int = 30) -> str:
    """Short preview for diff output; collapses whitespace so it stays one line."""
    flat = " ".join(text.split())
    return flat if len(flat) <= around * 2 else f"{flat[:around]}…{flat[-around:]}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true", help="Write changes (default: preview only)"
    )
    args = parser.parse_args()

    db = next(get_db())
    repo = CharacterRepository(db)

    changed_rows = 0
    changed_fields = 0
    for character in repo.find_all():
        row_changed = False
        for name in _BULLET_LIST_FIELDS:
            value = getattr(character, name)
            if not value:
                continue
            normalized = normalize_bullet_list(value)
            if normalized != value:
                items = normalized.count("\n\n") + 1
                print(
                    f"{character.name!r} .{name}: {_snippet(value)!r} -> {items} item(s), bullets dropped"
                )
                setattr(character, name, normalized)
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
        print(
            f"\nPreview only: {changed_fields} field(s) across {changed_rows} character(s) would change."
        )
        print("Re-run with --apply to write.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
