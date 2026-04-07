"""Dependency injection factories for character module"""

from typing import Annotated

from fastapi import Depends

from src.character.repository import CharacterRepository
from src.character.service import CharacterService
from src.core.persistence import DbSession


def get_character_repository(db: DbSession) -> CharacterRepository:
    """Factory for CharacterRepository with DB injected"""
    return CharacterRepository(db)


def get_character_service(
    character_repo: Annotated[CharacterRepository, Depends(get_character_repository)],
) -> CharacterService:
    """Factory for CharacterService with repository injected"""
    return CharacterService(character_repo)


CharacterServiceDep = Annotated[CharacterService, Depends(get_character_service)]
CharacterRepositoryDep = Annotated[CharacterRepository, Depends(get_character_repository)]
