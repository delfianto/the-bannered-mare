#!/usr/bin/env python3
"""Export a character from the database as a TavernCard.

Resolves a character by name or id and writes a V2 PNG (embedded JSON, with the
character's lorebook re-embedded as `character_book`) or a JSON card.

Run with the backend virtualenv; needs the backend env (.env / DATABASE_URL) and a
migrated database:

    backend/.venv/bin/python scripts/export_card.py --name "Daro-Soraya"
    backend/.venv/bin/python scripts/export_card.py --name "Daro-Soraya" -o characters/daro_soraya.png
    backend/.venv/bin/python scripts/export_card.py --id ab12cd34ef56 --format json -o card.json
"""

import argparse
import os
import sys

# Backend lives one level up from this repo-root scripts/ folder.
_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, _BACKEND)

from src.character.repository import CharacterRepository
from src.character.service import CharacterService
from src.core.persistence.database import get_db
from src.lore.repository import LoreEntryRepository, LoreRepository
from src.lore.service import LoreService


def slugify(name: str) -> str:
    """character_name.png-style slug from a display name."""
    lowered = "".join(ch if ch.isalnum() else "_" for ch in name.lower())
    return "_".join(filter(None, lowered.split("_"))) or "character"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a character as a TavernCard.")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--name", help="Character name (exact match)")
    target.add_argument("--id", dest="char_id", help="Character id")
    parser.add_argument("--format", choices=["png", "json"], default="png")
    parser.add_argument("-o", "--out", help="Output path (default: ./<slug>.<format>)")
    args = parser.parse_args()

    db = next(get_db())
    repo = CharacterRepository(db)
    service = CharacterService(repo, LoreService(LoreRepository(db), LoreEntryRepository(db)))

    character = repo.find_by_id(args.char_id) if args.char_id else repo.find_by_name(args.name)
    if not character:
        print(f"Character not found: {args.char_id or args.name}", file=sys.stderr)
        return 1

    out = args.out or f"{slugify(character.name)}.{args.format}"
    if args.format == "png":
        with open(out, "wb") as fh:
            fh.write(service.export_as_png(character.id))
    else:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(service.export_as_json(character.id))

    print(f"Exported {character.name} ({character.id}) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
