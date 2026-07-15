"""Dependency injection factories for profile module"""

from typing import Annotated

from fastapi import Depends

from src.core.persistence import DbSession, UnitOfWork
from src.model.repository import ModelRepository
from src.persona.repository import PersonaRepository
from src.preset.repository import PresetRepository
from src.profile.repository import ProfileRepository
from src.profile.service import ProfileService
from src.prompt_template.repository import PromptTemplateRepository


def get_profile_repository(db: DbSession) -> ProfileRepository:
    """Factory for ProfileRepository with DB injected"""
    return ProfileRepository(db)


def get_profile_service(db: DbSession) -> ProfileService:
    """Factory for ProfileService with its repository and lookup repositories.

    The lookup repositories share the same session and back FK validation on create/update.
    """
    return ProfileService(
        profile_repo=ProfileRepository(db),
        template_repo=PromptTemplateRepository(db),
        preset_repo=PresetRepository(db),
        persona_repo=PersonaRepository(db),
        model_repo=ModelRepository(db),
        uow=UnitOfWork(db),
    )


ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]
ProfileRepositoryDep = Annotated[ProfileRepository, Depends(get_profile_repository)]
