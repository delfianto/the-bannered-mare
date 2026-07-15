"""Dependency injection factories for character module"""

from typing import Annotated

from fastapi import Depends

from src.character.repository import CharacterRepository
from src.character.service import CharacterService
from src.core.persistence import DbSession
from src.lore.dependencies import get_lore_service
from src.lore.service import LoreService


def get_character_repository(db: DbSession) -> CharacterRepository:
    """Factory for CharacterRepository with DB injected"""
    return CharacterRepository(db)


def get_character_service(
    character_repo: Annotated[CharacterRepository, Depends(get_character_repository)],
    lore_service: Annotated[LoreService, Depends(get_lore_service)],
) -> CharacterService:
    """Factory for CharacterService with its lore seam injected.

    The lore service shares the request session so character import/export reads
    & writes the lorebook in the same transaction as the character.
    """
    return CharacterService(character_repo, lore_service)


CharacterServiceDep = Annotated[CharacterService, Depends(get_character_service)]
CharacterRepositoryDep = Annotated[CharacterRepository, Depends(get_character_repository)]
