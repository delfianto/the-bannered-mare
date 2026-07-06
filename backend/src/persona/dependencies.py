"""Dependency injection factories for persona module"""

from typing import Annotated

from fastapi import Depends

from src.core.persistence import DbSession
from src.persona.repository import PersonaRepository
from src.persona.service import PersonaService


def get_persona_repository(db: DbSession) -> PersonaRepository:
    """Factory for PersonaRepository with DB injected"""
    return PersonaRepository(db)


def get_persona_service(
    persona_repo: Annotated[PersonaRepository, Depends(get_persona_repository)],
) -> PersonaService:
    """Factory for PersonaService with repository injected"""
    return PersonaService(persona_repo)


PersonaServiceDep = Annotated[PersonaService, Depends(get_persona_service)]
PersonaRepositoryDep = Annotated[PersonaRepository, Depends(get_persona_repository)]
