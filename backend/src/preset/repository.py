"""Data access layer for Preset entities"""

from sqlalchemy.orm import Session

from src.core.persistence import DefaultableRepository, NamedRepository
from src.preset.models import Preset


class PresetRepository(NamedRepository[Preset], DefaultableRepository[Preset]):
    """Repository for Preset data access (name lookup + default-toggling from mixins)."""

    def __init__(self, db: Session):
        super().__init__(db, Preset)
