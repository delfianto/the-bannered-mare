"""Data access layer for Profile entities"""

from sqlalchemy.orm import Session

from src.core.persistence import DefaultableRepository, NamedRepository
from src.profile.models import Profile


class ProfileRepository(NamedRepository[Profile], DefaultableRepository[Profile]):
    """Repository for Profile data access (name lookup + default-toggling from mixins)."""

    def __init__(self, db: Session):
        super().__init__(db, Profile)
