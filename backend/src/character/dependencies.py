"""Dependency injection factories for character module"""

from typing import Annotated

from fastapi import Depends

from src.character.repository import CharacterRepository
from src.character.service import CharacterService
from src.core.persistence import DbSession
from src.lore.repository import LoreEntryRepository, LoreRepository


def get_character_repository(db: DbSession) -> CharacterRepository:
    """Factory for CharacterRepository with DB injected"""
    return CharacterRepository(db)


def get_character_service(
    character_repo: Annotated[CharacterRepository, Depends(get_character_repository)],
    db: DbSession,
) -> CharacterService:
    """Factory for CharacterService with repositories injected.

    The lore repositories share the request session so character import/export
    reads & writes the lorebook in the same transaction as the character.
    """
    return CharacterService(character_repo, LoreRepository(db), LoreEntryRepository(db))


CharacterServiceDep = Annotated[CharacterService, Depends(get_character_service)]
CharacterRepositoryDep = Annotated[CharacterRepository, Depends(get_character_repository)]
