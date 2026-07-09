"""Backfill multi-size avatars for existing characters and personas.

For every character/persona that has an original avatar on disk, (re)generate
the large (<=512px full portrait) and head-crop (256px square) derivatives from
the stored original and record the new ``avatar_large`` path. The head crop also
replaces the old 128px full-portrait ``avatar_thumbnail``. Idempotent — safe to
re-run.

Usage (from the repo root):

    backend/.venv/bin/python scripts/backfill_avatar_sizes.py
"""

import os
import sys

# Backend lives one level up from this repo-root scripts/ folder.
_BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, _BACKEND)

from sqlalchemy.orm import Session

from src.core.persistence.database import SessionLocal
from src.core.persistence.models.character import Character
from src.core.persistence.models.persona import Persona
from src.core.utils.storage import generate_avatar_derivatives


def _backfill(session: Session, model: type, entity_type: str) -> int:
    updated = 0
    rows = session.query(model).filter(model.avatar.isnot(None)).all()
    for row in rows:
        large_rel, head_rel = generate_avatar_derivatives(entity_type, row.id)
        if not large_rel:
            print(f"  ! {entity_type}/{row.id} ({row.name}): no original on disk — skipped")
            continue
        row.avatar_large = large_rel
        row.avatar_thumbnail = head_rel
        updated += 1
        print(f"  ok {entity_type}/{row.id} ({row.name})")
    return updated


def main() -> None:
    with SessionLocal() as session:
        print("Characters:")
        characters = _backfill(session, Character, "characters")
        print("Personas:")
        personas = _backfill(session, Persona, "personas")
        session.commit()
    print(f"\nBackfilled {characters} character(s) and {personas} persona(s).")


if __name__ == "__main__":
    main()
