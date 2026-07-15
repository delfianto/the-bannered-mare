"""Dependency injection factories for model family module"""

from typing import Annotated

from fastapi import Depends

from src.core.persistence import DbSession, UnitOfWork
from src.model_family.repository import ModelFamilyRepository
from src.model_family.service import ModelFamilyService


def get_model_family_repository(db: DbSession) -> ModelFamilyRepository:
    """Factory for ModelFamilyRepository with DB injected"""
    return ModelFamilyRepository(db)


def get_model_family_service(
    family_repo: Annotated[ModelFamilyRepository, Depends(get_model_family_repository)],
) -> ModelFamilyService:
    """Factory for ModelFamilyService with repository injected"""
    return ModelFamilyService(family_repo, uow=UnitOfWork(family_repo.db))


ModelFamilyServiceDep = Annotated[ModelFamilyService, Depends(get_model_family_service)]
ModelFamilyRepositoryDep = Annotated[ModelFamilyRepository, Depends(get_model_family_repository)]
