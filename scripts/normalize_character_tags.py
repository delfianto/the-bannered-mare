#!/usr/bin/env python3
"""Backfill: Title-Case existing character tags for casing consistency.

New imports and create/update calls are normalized automatically (see
``src.character.service._normalize_tags``); this is a one-off fixup for rows
that were imported before that existed. Prints a per-tag diff and, by default,
only previews -- pass --apply to write the changes.

Run with the backend virtualenv; needs the backend env (.env / DATABASE_URL):

    backend/.venv/bin/python scripts/normalize_character_tags.py            # preview
    backend/.venv/bin/python scripts/normalize_character_tags.py --apply    # write
"""

import argparse
import os
import sys

# Backend lives one level up from this repo-root scripts/ folder.
_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, _BACKEND)

from src.character.repository import CharacterRepository
from src.character.service import _normalize_tags
from src.core.persistence.database import get_db


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write changes (default: preview only)")
    args = parser.parse_args()

    db = next(get_db())
    repo = CharacterRepository(db)

    changed_rows = 0
    changed_tags = 0
    for character in repo.find_all():
        tags = character.tags
        if not tags:
            continue

        normalized = _normalize_tags(tags)
        if normalized == tags:
            continue

        for old, new in zip(tags, normalized or [], strict=True):
            if old != new:
                print(f"{character.name!r}: {old!r} -> {new!r}")
                changed_tags += 1

        character.tags = normalized
        changed_rows += 1
        if args.apply:
            repo.update(character)

    if args.apply:
        db.commit()
        print(f"\nApplied: {changed_tags} tag(s) across {changed_rows} character(s).")
    else:
        print(f"\nPreview only: {changed_tags} tag(s) across {changed_rows} character(s) would change.")
        print("Re-run with --apply to write.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
