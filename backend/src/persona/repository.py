"""Data access layer for Persona entities"""

from sqlalchemy.orm import Session

from src.core.persistence import DefaultableRepository
from src.persona.models import Persona


class PersonaRepository(DefaultableRepository[Persona]):
    """Repository for Persona data access.

    Ordered listing, filtered pagination, and default-toggling all come from the
    base repository + ``DefaultableRepository`` mixin.
    """

    def __init__(self, db: Session):
        super().__init__(db, Persona)
