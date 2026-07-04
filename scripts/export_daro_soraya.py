import asyncio
import os
import sys

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.persistence.database import get_db
from src.character.service import CharacterService
from src.character.repository import CharacterRepository

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

    # Save to _character_cards/daro_soraya.png
    dest_path = os.path.join("_character_cards", "daro_soraya.png")
    with open(dest_path, "wb") as f:
        f.write(png_bytes)

    print(f"Successfully exported Daro-Soraya to {dest_path}")

if __name__ == "__main__":
    asyncio.run(main())
