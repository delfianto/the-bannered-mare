"""Preset business logic service"""

from typing import Any

from src.core.base_service import get_or_404, set_as_default
from src.core.persistence import UnitOfWork, gen_id
from src.preset.models import Preset
from src.preset.repository import PresetRepository


class PresetService:
    """Service for preset-related business logic"""

    def __init__(self, preset_repo: PresetRepository, uow: UnitOfWork | None = None):
        self.preset_repo = preset_repo
        # The unit of work owns the transaction boundary; it wraps the same session
        # the repos share. Fallback keeps direct `PresetService(...)` construction
        # (tests) valid — the DI factory injects the request-scoped UoW.
        self.uow = uow or UnitOfWork(preset_repo.db)

    def list_all(self) -> list[Preset]:
        """List all presets"""
        return self.preset_repo.find_all_ordered()

    def list_paginated(self, limit: int = 10, offset: int = 0) -> tuple[list[Preset], int]:
        """List presets with pagination"""
        return self.preset_repo.find_paginated_ordered(limit, offset)

    def get_by_id(self, preset_id: str) -> Preset:
        """Get preset by ID, raise 404 if not found"""
        return get_or_404(self.preset_repo, preset_id, "Preset")

    def create(
        self,
        name: str,
        description: str | None = None,
        parameters: dict[str, Any] | None = None,
        is_default: bool = False,
    ) -> Preset:
        """Create new preset"""
        if is_default:
            self.preset_repo.unset_all_defaults()

        preset = Preset(
            id=gen_id(),
            name=name,
            description=description,
            parameters=parameters or {},
            is_default=is_default,
        )
        created = self.preset_repo.create(preset)
        self.uow.commit()
        return created

    # --- SillyTavern import seam (BE-H2) ---

    def find_by_name(self, name: str) -> Preset | None:
        """Look up a preset by exact name (import unique-naming)."""
        return self.preset_repo.find_by_name(name)

    def create_imported(
        self,
        name: str,
        description: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> Preset:
        """Create a preset from a trusted import. Flush-only — participates in the
        caller's unit of work so the whole ST import commits as one transaction."""
        preset = Preset(
            id=gen_id(),
            name=name,
            description=description,
            parameters=parameters or {},
            is_default=False,
        )
        return self.preset_repo.create(preset)

    def update(
        self,
        preset_id: str,
        name: str | None = None,
        description: str | None = None,
        parameters: dict[str, Any] | None = None,
        is_default: bool | None = None,
    ) -> Preset:
        """Update preset"""
        preset = self.get_by_id(preset_id)

        if is_default:
            self.preset_repo.unset_all_defaults(exclude_id=preset_id)

        if name is not None:
            preset.name = name
        if description is not None:
            preset.description = description
        if parameters is not None:
            preset.parameters = parameters
        if is_default is not None:
            preset.is_default = is_default

        updated = self.preset_repo.update(preset)
        self.uow.commit()
        return updated

    def delete(self, preset_id: str) -> None:
        """Delete preset"""
        preset = self.get_by_id(preset_id)
        self.preset_repo.delete(preset)
        self.uow.commit()

    def set_default(self, preset_id: str) -> Preset:
        """Set preset as default"""
        return set_as_default(self.preset_repo, self.get_by_id(preset_id), self.uow)
