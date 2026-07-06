"""Dependency injection factories for lore module"""

from typing import Annotated

from fastapi import Depends

from src.core.persistence import DbSession
from src.lore.repository import LoreEntryRepository, LoreRepository
from src.lore.service import LoreService


def get_lore_repository(db: DbSession) -> LoreRepository:
    return LoreRepository(db)


def get_lore_entry_repository(db: DbSession) -> LoreEntryRepository:
    return LoreEntryRepository(db)


def get_lore_service(
    lore_repo: Annotated[LoreRepository, Depends(get_lore_repository)],
    entry_repo: Annotated[LoreEntryRepository, Depends(get_lore_entry_repository)],
) -> LoreService:
    return LoreService(lore_repo, entry_repo)


LoreServiceDep = Annotated[LoreService, Depends(get_lore_service)]
LoreRepositoryDep = Annotated[LoreRepository, Depends(get_lore_repository)]
