"""Dependency injection factories for provider module"""

from typing import Annotated

from fastapi import Depends

from src.core.persistence import DbSession, UnitOfWork
from src.provider.model_cache import ModelListCache, get_model_list_cache
from src.provider.repository import ProviderRepository
from src.provider.service import ProviderService


def get_provider_repository(db: DbSession) -> ProviderRepository:
    """Factory for ProviderRepository with DB injected"""
    return ProviderRepository(db)


def get_provider_service(
    provider_repo: Annotated[ProviderRepository, Depends(get_provider_repository)],
    model_cache: Annotated[ModelListCache, Depends(get_model_list_cache)],
) -> ProviderService:
    """Factory for ProviderService with repository and model cache injected"""
    return ProviderService(provider_repo, model_cache, uow=UnitOfWork(provider_repo.db))


ProviderServiceDep = Annotated[ProviderService, Depends(get_provider_service)]
ProviderRepositoryDep = Annotated[ProviderRepository, Depends(get_provider_repository)]
