"""Dependency injection factories for provider module"""

from typing import Annotated

from fastapi import Depends

from src.core.persistence import DbSession
from src.provider.model_cache import ModelListCache, get_model_list_cache
from src.provider.model_service import ProviderModelService
from src.provider.repository import ProviderRepository
from src.provider.service import ProviderService


def get_provider_repository(db: DbSession) -> ProviderRepository:
    """Factory for ProviderRepository with DB injected"""
    return ProviderRepository(db)


def get_provider_service(
    provider_repo: Annotated[ProviderRepository, Depends(get_provider_repository)],
) -> ProviderService:
    """Factory for ProviderService (provider entity CRUD)"""
    return ProviderService(provider_repo)


def get_provider_model_service(
    provider_repo: Annotated[ProviderRepository, Depends(get_provider_repository)],
    model_cache: Annotated[ModelListCache, Depends(get_model_list_cache)],
) -> ProviderModelService:
    """Factory for ProviderModelService (discovery + cache + runtime actions)"""
    return ProviderModelService(provider_repo, model_cache)


ProviderServiceDep = Annotated[ProviderService, Depends(get_provider_service)]
ProviderModelServiceDep = Annotated[ProviderModelService, Depends(get_provider_model_service)]
ProviderRepositoryDep = Annotated[ProviderRepository, Depends(get_provider_repository)]
