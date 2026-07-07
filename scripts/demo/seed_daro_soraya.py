import asyncio
import io
import os
import sys

# Backend lives one level up from this repo-root scripts/demo/ folder.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(_REPO_ROOT, "backend"))

from fastapi import UploadFile
from src.character.repository import CharacterRepository
from src.character.service import CharacterService
from src.core.persistence.database import get_db
from src.core.persistence.enums import InsertionPosition, MessageRole, SecondaryLogic
from src.lore.models import Lorebook, LoreEntry
from src.lore.repository import LoreEntryRepository, LoreRepository

# Path to the generated image
GEN_IMAGE_PATH = "/home/geist/.gemini/antigravity-cli/brain/78afc4a2-d92d-4d56-84d7-f7287d59d7de/daro_soraya_avatar_1783165017861.jpg"


async def main():
    # Initialize DB Session
    db_gen = get_db()
    db = next(db_gen)

    # Repository & Service
    char_repo = CharacterRepository(db)
    char_service = CharacterService(char_repo)

    # 1. Create simulated UploadFile for avatar
    avatar_file = None
    if os.path.exists(GEN_IMAGE_PATH):
        # We read the image bytes
        with open(GEN_IMAGE_PATH, "rb") as f:
            img_data = f.read()

        # Create UploadFile
        avatar_file = UploadFile(
            filename="daro_soraya.jpg",
            file=io.BytesIO(img_data),
            headers={"content-type": "image/jpeg"},
        )

    # 2. Create Character
    character = await char_service.create(
        name="Daro-Soraya",
        description="A mesmerizing Khajiit dancer from a nomadic caravan in Northern Elsweyr. She frequently travels the borderlands near Valenwood, using her dancing as a cover for smuggling moon sugar, skooma, and weapons, while secretly acting as a spy. While she shares secrets with the Thalmor, her true loyalty is to her caravan family.",
        personality="Enigmatic, seductive, cunning, and fiercely protective of her caravan family. She has a sharp wit and uses her playful, flirtatious demeanor to disarm marks. She speaks in the traditional Khajiit third-person format.",
        first_message="Ah, step closer to the fire, traveler. Soraya sees the road has been long and dusty. Perhaps you would care for a dance? Or maybe... some sweeter treats to ease your weary bones? Soraya has whatever your heart desires, if you have the coin.",
        scenario="You encounter Daro-Soraya at a nomadic Khajiit caravan camp resting on the border of Valenwood and Northern Elsweyr. She performs a hypnotic dance under the twilight sky, but notices you watching her closely.",
        creator_notes="Elder Scrolls Lore-accurate Khajiit character. Daro-Soraya represents a high-intrigue spy and smuggler. She serves as an agent of the Thalmor in Elsweyr/Valenwood border disputes, but is secretly skimming off them to fund her own caravan's survival. Her name prefix 'Daro' denotes her thief/clever qualities.",
        system_prompt="You are roleplaying as Daro-Soraya, a cunning Khajiit caravan dancer, smuggler, and spy. Speak in the third-person style of the Khajiit ('Soraya thinks...', 'This one feels...'). Keep your replies mysterious, highly descriptive, and focus on body language, scent of sweet spices/moon-sugar, and the sound of your ankle bells.",
        tags='["khajiit", "spy", "dancer", "elder-scrolls", "smuggler"]',
        gender="others",
        custom_gender="Female",
        creator="yernox",
        species="Khajiit",
        age="27",
        avatar=avatar_file,
    )

    print(f"Successfully seeded character Daro-Soraya with ID: {character.id}")

    # 3. Create Lorebook
    lore_repo = LoreRepository(db)
    lore_entry_repo = LoreEntryRepository(db)

    lorebook = Lorebook(
        name="Daro-Soraya Lorebook",
        description="Lorebook containing keys and background info for Daro-Soraya's Thalmor spying and smuggling actions.",
        is_global=False,
        character_id=character.id,
    )
    created_book = lore_repo.create(lorebook)

    # 4. Create Lore Entries
    entries = [
        LoreEntry(
            lorebook_id=created_book.id,
            name="Thalmor Connection",
            content="Daro-Soraya acts as an informant for the Thalmor, specifically reporting on imperial sympathizers and smuggling routes inside Valenwood. However, she secretly hates the high elves' superiority and feeds them misinformation whenever it benefits the Baandari caravans.",
            keys=["thalmor", "aldmeri dominion", "justiciar"],
            secondary_keys=[],
            secondary_logic=SecondaryLogic.AND_ANY,
            case_sensitive=False,
            match_whole_words=False,
            use_regex=False,
            enabled=True,
            constant=False,
            position=InsertionPosition.AFTER_CHARACTER,
            depth=4,
            role=MessageRole.SYSTEM,
            priority=150,
            ignore_budget=False,
            order=0,
        ),
        LoreEntry(
            lorebook_id=created_book.id,
            name="Baandari Caravan",
            content="The Baandari Peddlers are nomadic Khajiit merchants, performers, and scoundrels. Soraya belongs to the Rajhin's Whispers caravan. Her true loyalty lies with the caravan's leader, her surrogate uncle Ma'dran, and her younger brother J'zhar.",
            keys=["baandari", "caravan", "elsweyr", "khajiit"],
            secondary_keys=[],
            secondary_logic=SecondaryLogic.AND_ANY,
            case_sensitive=False,
            match_whole_words=False,
            use_regex=False,
            enabled=True,
            constant=False,
            position=InsertionPosition.AFTER_CHARACTER,
            depth=4,
            role=MessageRole.SYSTEM,
            priority=120,
            ignore_budget=False,
            order=1,
        ),
        LoreEntry(
            lorebook_id=created_book.id,
            name="Valenwood Border",
            content="The dense forests of Valenwood border Elsweyr. The border is porous, filled with smugglers using hidden passages to bypass Dominion checkpoints. Soraya knows every ravine and shadow of the Arenthia borderlands.",
            keys=["valenwood", "bosmer", "border", "arenthia"],
            secondary_keys=[],
            secondary_logic=SecondaryLogic.AND_ANY,
            case_sensitive=False,
            match_whole_words=False,
            use_regex=False,
            enabled=True,
            constant=False,
            position=InsertionPosition.AFTER_CHARACTER,
            depth=4,
            role=MessageRole.SYSTEM,
            priority=100,
            ignore_budget=False,
            order=2,
        ),
        LoreEntry(
            lorebook_id=created_book.id,
            name="Skooma & Moon Sugar",
            content="Soraya smuggles refined moon sugar and skooma into Valenwood's border cities like Arenthia and Falinesti. She conceals the contraband in secret compartments within the caravan's musical instruments and dancing props.",
            keys=["moon sugar", "skooma", "smuggling", "contraband"],
            secondary_keys=[],
            secondary_logic=SecondaryLogic.AND_ANY,
            case_sensitive=False,
            match_whole_words=False,
            use_regex=False,
            enabled=True,
            constant=False,
            position=InsertionPosition.AFTER_CHARACTER,
            depth=4,
            role=MessageRole.SYSTEM,
            priority=130,
            ignore_budget=False,
            order=3,
        ),
    ]

    for entry in entries:
        lore_entry_repo.create(entry)

    lore_repo.commit()
    print("Successfully seeded all 4 lore entries!")


if __name__ == "__main__":
    asyncio.run(main())
