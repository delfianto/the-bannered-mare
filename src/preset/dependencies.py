"""Dependency injection factories for preset module"""

from typing import Annotated

from fastapi import Depends

from src.core.persistence import DbSession
from src.preset.repository import PresetRepository
from src.preset.service import PresetService


def get_preset_repository(db: DbSession) -> PresetRepository:
    """Factory for PresetRepository with DB injected"""
    return PresetRepository(db)


def get_preset_service(
    preset_repo: Annotated[PresetRepository, Depends(get_preset_repository)],
) -> PresetService:
    """Factory for PresetService with repository injected"""
    return PresetService(preset_repo)


PresetServiceDep = Annotated[PresetService, Depends(get_preset_service)]
PresetRepositoryDep = Annotated[PresetRepository, Depends(get_preset_repository)]
