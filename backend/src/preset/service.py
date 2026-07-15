"""Preset business logic service"""

from typing import Any

from src.core.base_service import BaseCrudService, apply_update, set_as_default
from src.core.pagination import DEFAULT_PAGE_SIZE
from src.core.persistence import UnitOfWork, gen_id
from src.preset.models import Preset
from src.preset.repository import PresetRepository

_EDITABLE = {"name", "description", "parameters", "is_default"}


class PresetService(BaseCrudService[Preset, PresetRepository]):
    """Service for preset-related business logic (inherits list_all/get_by_id/delete)."""

    def __init__(self, preset_repo: PresetRepository, uow: UnitOfWork | None = None):
        # Fallback keeps direct `PresetService(...)` construction (tests) valid —
        # the DI factory injects the request-scoped UoW.
        super().__init__(preset_repo, uow or UnitOfWork(preset_repo.db), "Preset")

    def list_paginated(
        self, limit: int = DEFAULT_PAGE_SIZE, offset: int = 0
    ) -> tuple[list[Preset], int]:
        """List presets with pagination"""
        return self.repo.find_paginated_ordered(limit, offset)

    def create(
        self,
        name: str,
        description: str | None = None,
        parameters: dict[str, Any] | None = None,
        is_default: bool = False,
    ) -> Preset:
        """Create new preset"""
        if is_default:
            self.repo.unset_all_defaults()

        preset = Preset(
            id=gen_id(),
            name=name,
            description=description,
            parameters=parameters or {},
            is_default=is_default,
        )
        created = self.repo.create(preset)
        self.uow.commit()
        return created

    # --- SillyTavern import seam (BE-H2) ---

    def find_by_name(self, name: str) -> Preset | None:
        """Look up a preset by exact name (import unique-naming)."""
        return self.repo.find_by_name(name)

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
        return self.repo.create(preset)

    def update(
        self,
        preset_id: str,
        name: str | None = None,
        description: str | None = None,
        parameters: dict[str, Any] | None = None,
        is_default: bool | None = None,
    ) -> Preset:
        """Update preset (skip-on-None: only provided fields change)."""
        preset = self.get_by_id(preset_id)

        if is_default:
            self.repo.unset_all_defaults(exclude_id=preset_id)

        patch = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "is_default": is_default,
        }
        apply_update(preset, {k: v for k, v in patch.items() if v is not None}, _EDITABLE)

        updated = self.repo.update(preset)
        self.uow.commit()
        return updated

    def set_default(self, preset_id: str) -> Preset:
        """Set preset as default"""
        return set_as_default(self.repo, self.get_by_id(preset_id), self.uow)
