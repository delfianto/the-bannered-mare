#!/usr/bin/env python3
"""Backfill: recover real character names from role/title `name` fields.

The card `name` field doubles as the {{char}} prompt token and the storefront
listing title, so imported rows often carry SEO junk ("Mina — Your Mean and Bratty
Stepsister...") or a bare role ("Shy Cousin") while the real name sits in a "Name:"
line in the description. New imports fix this automatically (see
``src.character.card_parser.fill_canonical_name``); this is a one-off fixup for rows
imported before that existed. Only a `name` that isn't already a usable personal name
is touched, and only when a name-shaped candidate can be recovered -- an anonymous role
is left as-is. Prints a diff and, by default, only previews -- pass --apply to write.

Run with the backend virtualenv; needs the backend env (.env / DATABASE_URL):

    backend/.venv/bin/python scripts/normalize_character_names.py            # preview
    backend/.venv/bin/python scripts/normalize_character_names.py --apply    # write
"""

import argparse
import os
import sys

# Backend lives one level up from this repo-root scripts/ folder.
_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, _BACKEND)

from src.character.card_parser import ParsedCard, fill_canonical_name
from src.character.repository import CharacterRepository
from src.core.persistence.database import get_db


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write changes (default: preview only)")
    args = parser.parse_args()

    db = next(get_db())
    repo = CharacterRepository(db)

    changed_rows = 0
    for character in repo.find_all():
        pseudo_card = ParsedCard(
            name=character.name,
            description=character.description or "",
            personality=character.personality or "",
        )
        recovered = fill_canonical_name(pseudo_card).name
        if recovered != character.name:
            print(f"{character.name!r} -> {recovered!r}")
            character.name = recovered
            changed_rows += 1
            if args.apply:
                repo.update(character)

    if args.apply:
        db.commit()
        print(f"\nApplied: renamed {changed_rows} character(s).")
    else:
        print(f"\nPreview only: {changed_rows} character(s) would be renamed.")
        print("Re-run with --apply to write.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
