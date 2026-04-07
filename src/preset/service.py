"""Preset business logic service"""

from typing import Any

from fastapi import HTTPException

from src.core.persistence import gen_id
from src.preset.models import Preset
from src.preset.repository import PresetRepository


class PresetService:
    """Service for preset-related business logic"""

    def __init__(self, preset_repo: PresetRepository):
        self.preset_repo = preset_repo

    def list_all(self) -> list[Preset]:
        """List all presets"""
        return self.preset_repo.find_all_ordered()

    def list_paginated(self, limit: int = 10, offset: int = 0) -> tuple[list[Preset], int]:
        """List presets with pagination"""
        return self.preset_repo.find_paginated_with_count(limit, offset)

    def get_by_id(self, preset_id: str) -> Preset:
        """Get preset by ID, raise 404 if not found"""
        preset = self.preset_repo.find_by_id(preset_id)
        if not preset:
            raise HTTPException(status_code=404, detail="Preset not found")
        return preset

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
        self.preset_repo.commit()
        return created

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
        self.preset_repo.commit()
        return updated

    def delete(self, preset_id: str) -> None:
        """Delete preset"""
        preset = self.get_by_id(preset_id)
        self.preset_repo.delete(preset)
        self.preset_repo.commit()

    def set_default(self, preset_id: str) -> Preset:
        """Set preset as default"""
        preset = self.get_by_id(preset_id)

        self.preset_repo.unset_all_defaults()

        preset.is_default = True
        updated = self.preset_repo.update(preset)
        self.preset_repo.commit()
        return updated
