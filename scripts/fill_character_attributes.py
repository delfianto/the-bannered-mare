#!/usr/bin/env python3
"""Backfill: fill species/gender/age from labels baked into description/personality.

New imports do this automatically (see
``src.character.card_parser.fill_baked_in_attributes``); this is a one-off
fixup for rows that were imported before that existed. Only fills a field that
is currently blank -- never overwrites an existing value. Prints a per-field
diff and, by default, only previews -- pass --apply to write the changes.

Run with the backend virtualenv; needs the backend env (.env / DATABASE_URL):

    backend/.venv/bin/python scripts/fill_character_attributes.py            # preview
    backend/.venv/bin/python scripts/fill_character_attributes.py --apply    # write
"""

import argparse
import os
import sys

# Backend lives one level up from this repo-root scripts/ folder.
_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, _BACKEND)

from src.character.card_parser import ParsedCard, fill_baked_in_attributes
from src.character.repository import CharacterRepository
from src.character.service import _map_card_gender
from src.core.persistence.database import get_db


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write changes (default: preview only)")
    args = parser.parse_args()

    db = next(get_db())
    repo = CharacterRepository(db)

    changed_rows = 0
    changed_fields = 0
    for character in repo.find_all():
        has_gender_signal = character.gender is not None or character.custom_gender
        if character.age and character.species and has_gender_signal:
            continue  # nothing left to fill

        pseudo_card = ParsedCard(
            name=character.name,
            description=character.description or "",
            personality=character.personality or "",
            age=character.age or "",
            gender=character.gender.value if character.gender else "",
            custom_gender=character.custom_gender or "",
            species=character.species or "",
        )
        filled = fill_baked_in_attributes(pseudo_card)

        row_changed = False
        if not character.age and filled.age:
            print(f"{character.name!r} .age: None -> {filled.age!r}")
            character.age = filled.age
            row_changed = True
            changed_fields += 1

        if not character.species and filled.species:
            print(f"{character.name!r} .species: None -> {filled.species!r}")
            character.species = filled.species
            row_changed = True
            changed_fields += 1

        if not has_gender_signal and filled.gender:
            gender_enum, custom_gender = _map_card_gender(filled.gender, filled.custom_gender)
            if gender_enum is not None:
                print(f"{character.name!r} .gender: None -> {gender_enum.value!r}")
                character.gender = gender_enum
                character.custom_gender = custom_gender
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
