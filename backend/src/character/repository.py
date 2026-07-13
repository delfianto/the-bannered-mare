"""Data access layer for Character entities"""

from sqlalchemy.orm import Session

from src.character.models import Character
from src.core.persistence import NamedRepository


class CharacterRepository(NamedRepository[Character]):
    """Repository for Character data access.

    Name lookup, ordered listing, and filtered pagination all come from the base
    repository + ``NamedRepository`` mixin.
    """

    def __init__(self, db: Session):
        super().__init__(db, Character)
