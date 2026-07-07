import asyncio
import os
import sys

# Backend lives one level up from this repo-root scripts/demo/ folder.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(_REPO_ROOT, "backend"))

from src.character.repository import CharacterRepository
from src.character.service import CharacterService
from src.core.persistence.database import get_db


async def main():
    db_gen = get_db()
    db = next(db_gen)

    char_repo = CharacterRepository(db)
    char_service = CharacterService(char_repo)

    # Find Daro-Soraya
    character = char_repo.find_by_name("Daro-Soraya")
    if not character:
        print("Daro-Soraya not found in database!")
        return

    # Export as PNG
    png_bytes = char_service.export_as_png(character.id)

    # Save to the repo-root characters/ collection (test-data cards).
    dest_path = os.path.join(_REPO_ROOT, "characters", "daro_soraya.png")
    with open(dest_path, "wb") as f:
        f.write(png_bytes)

    print(f"Successfully exported Daro-Soraya to {dest_path}")


if __name__ == "__main__":
    asyncio.run(main())
