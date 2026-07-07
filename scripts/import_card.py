#!/usr/bin/env python3
"""Import / seed character cards into the database.

Imports one or more TavernCard PNG/JSON cards via the backend's CharacterService:
each becomes a Character, its embedded `character_book` becomes a Lorebook + entries,
and (for PNG cards) the image is saved as the avatar. Works with any card — e.g. the
sample cards in ./characters/.

Run with the backend virtualenv; needs the backend env (.env / DATABASE_URL) and a
migrated database:

    backend/.venv/bin/python scripts/import_card.py CARD [CARD ...]   # specific cards
    backend/.venv/bin/python scripts/import_card.py characters/       # every card in a dir
    backend/.venv/bin/python scripts/import_card.py characters/*.png  # globs work
"""

import argparse
import asyncio
import io
import os
import sys

# Backend lives one level up from this repo-root scripts/ folder.
_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, _BACKEND)

from fastapi import UploadFile
from starlette.datastructures import Headers

from src.character.repository import CharacterRepository
from src.character.service import CharacterService
from src.core.persistence.database import get_db

_CONTENT_TYPE = {".png": "image/png", ".json": "application/json"}


def collect(paths: list[str]) -> list[str]:
    """Expand any directories into the card files they contain."""
    files: list[str] = []
    for path in paths:
        if os.path.isdir(path):
            files.extend(
                os.path.join(path, name)
                for name in sorted(os.listdir(path))
                if os.path.splitext(name)[1].lower() in _CONTENT_TYPE
            )
        else:
            files.append(path)
    return files


async def main() -> int:
    parser = argparse.ArgumentParser(description="Import character cards into the database.")
    parser.add_argument("cards", nargs="+", help="Card file(s) or a directory of cards")
    args = parser.parse_args()

    files = collect(args.cards)
    if not files:
        print("No .png/.json cards found.", file=sys.stderr)
        return 1

    db = next(get_db())
    service = CharacterService(CharacterRepository(db))

    imported = failed = 0
    for path in files:
        ext = os.path.splitext(path)[1].lower()
        if ext not in _CONTENT_TYPE:
            print(f"skip  {os.path.basename(path)}  (not a .png/.json card)")
            continue
        try:
            with open(path, "rb") as fh:
                upload = UploadFile(
                    filename=os.path.basename(path),
                    file=io.BytesIO(fh.read()),
                    headers=Headers({"content-type": _CONTENT_TYPE[ext]}),
                )
            character = await service.import_card(upload)
            print(f"ok    {os.path.basename(path)}  ->  {character.name} ({character.id})")
            imported += 1
        except Exception as exc:  # noqa: BLE001 — one bad card must not abort the batch
            db.rollback()
            print(f"FAIL  {os.path.basename(path)}  ->  {exc}", file=sys.stderr)
            failed += 1

    print(f"\nImported {imported} card(s), {failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
